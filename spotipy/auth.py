import base64
import json
import logging
import time
from http import HTTPStatus

import requests
import requests.adapters

from spotipy import exceptions

_logger = logging.getLogger(__name__)


def request_token(payload: dict, client_id: str, client_secret: str, requests_session: requests.Session = None) -> dict:
    auth_header = base64.b64encode("{}:{}".format(client_id, client_secret).encode("ascii"))
    headers = {"Authorization": "Basic {}".format(auth_header.decode("ascii"))}
    if not requests_session:
        requests_session = requests.Session()
    response = requests_session.post("https://accounts.spotify.com/api/token", data=payload, headers=headers)
    if response.status_code != HTTPStatus.OK:
        error_message = ""
        if response.content:
            error = response.json()
            error_message = "{}. description: {}".format(error["error"], error["error_description"])
        raise exceptions.AuthorizationError(response.status_code, error_message)
    return response.json()


def is_token_expired(expires_at: int):
    now = int(time.time())
    return expires_at - now < 30


class SpotifyAuthProvider:
    def make_authorization_headers(self) -> dict:
        raise NotImplementedError

    @property
    def access_token(self):
        raise NotImplementedError


class PlainAccessToken(SpotifyAuthProvider):
    def __init__(self, access_token: str, requests_session: requests.Session = None):
        """
        You can either provide a client_id and client_secret to the
        constructor or set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET
        environment variables
        """

        self._access_token = access_token

        if isinstance(requests_session, requests.Session):
            self._session = requests_session
        else:
            self._session = requests.Session()

        self._session.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))

    def make_authorization_headers(self) -> dict:
        return {"Authorization": "Bearer {}".format(self._access_token)}

    @property
    def access_token(self):
        return self._access_token


class ClientCredentials(SpotifyAuthProvider):
    def __init__(self, client_id: str, client_secret: str, requests_session: requests.Session = None):
        """
        You can either provide a client_id and client_secret to the
        constructor or set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET
        environment variables
        """

        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = None
        self._access_token_expires = None

        if isinstance(requests_session, requests.Session):
            self._session = requests_session
        else:
            self._session = requests.Session()

        self._session.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))

    def make_authorization_headers(self) -> dict:
        if not self._access_token or is_token_expired(self._access_token_expires):
            self._request_access_token()

        return {"Authorization": "Bearer {}".format(self._access_token)}

    @property
    def access_token(self):
        return self._access_token

    def _request_access_token(self):
        """Gets client credentials access token """
        payload = {"grant_type": "client_credentials"}

        now = int(time.time())
        token_info = request_token(payload, self.client_id, self.client_secret, self._session)
        self._access_token = token_info["access_token"]
        self._access_token_expires = now + token_info["expires_in"]


class AuthorizationCode(SpotifyAuthProvider):
    """
    Implements Authorization Code Flow for Spotify's OAuth implementation.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        access_token: str = None,
        access_token_expires_at: int = None,
        persist_file_path=None,
        requests_session: requests.Session = None,
    ):
        """
            Creates a SpotifyOAuth object

            Parameters:
                 - client_id - the client id of your app
                 - client_secret - the client secret of your app
                 - redirect_uri - the redirect URI of your app
                 - state - security state
                 - scope - the desired scope of the request
                 - cache_path - path to location to save tokens
        """

        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._access_token = access_token
        self._access_token_expires_at = access_token_expires_at
        if (access_token is not None) != (access_token_expires_at is not None):
            raise ValueError("when supplying access_token, access_token_expires_at must be supplied as well")
        self._persist_file_path = persist_file_path

        if not requests_session:
            self.session = requests.Session()

    @property
    def access_token(self):
        return self._access_token

    def save(self):
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token,
        }
        with open(self._persist_file_path, "w") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, persist_file_path: str, requests_session: requests.Session = None):
        with open(persist_file_path) as f:
            data = json.load(f)

        return cls(
            data["client_id"],
            data["client_secret"],
            data["refresh_token"],
            persist_file_path=persist_file_path,
            requests_session=requests_session,
        )

    def make_authorization_headers(self) -> dict:
        if not self._access_token or is_token_expired(self._access_token_expires_at):
            self._request_access_token()

        return {"Authorization": "Bearer {}".format(self._access_token)}

    def _request_access_token(self):
        payload = {"refresh_token": self._refresh_token, "grant_type": "refresh_token"}
        now = int(time.time())
        token_info = request_token(payload, self._client_id, self._client_secret, self.session)
        self._access_token = token_info["access_token"]
        self._access_token_expires_at = token_info["expires_in"] + now
        if self._persist_file_path:
            self.save()
