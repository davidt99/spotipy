import base64
import json
import logging
import os
import time
from http import HTTPStatus
from typing import Sequence
from typing import Union
from urllib import parse

import requests

from spotipy import exceptions

_logger = logging.getLogger(__name__)


def _make_authorization_headers(client_id, client_secret):
    auth_header = base64.b64encode("{}:{}".format(client_id, client_secret))
    return {"Authorization": "Basic {}".format(auth_header)}


def is_token_expired(token_info):
    now = int(time.time())
    return token_info["expires_at"] - now < 60


class SpotifyClientCredentials(object):
    OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"

    def __init__(self, client_id=None, client_secret=None, requests_session=None):
        """
        You can either provide a client_id and client_secret to the
        constructor or set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET
        environment variables
        """
        if not client_id:
            client_id = os.getenv("SPOTIPY_CLIENT_ID")

        if not client_secret:
            client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")

        if not client_id:
            raise ValueError("No client id")

        if not client_secret:
            raise ValueError("No client secret")

        self.client_id = client_id
        self.client_secret = client_secret
        self.token_info = None
        if isinstance(requests_session, requests.Session):
            self._session = requests_session
        else:
            self._session = requests.Session()

    def get_access_token(self):
        """
        If a valid access token is in memory, returns it
        Else fetches a new token and returns it
        """
        if self.token_info and not is_token_expired(self.token_info):
            return self.token_info["access_token"]

        token_info = self._request_access_token()
        token_info = self._add_custom_values_to_token_info(token_info)
        self.token_info = token_info
        return self.token_info["access_token"]

    def _request_access_token(self):
        """Gets client credentials access token """
        payload = {"grant_type": "client_credentials"}

        headers = _make_authorization_headers(self.client_id, self.client_secret)

        response = self._session.post(
            self.OAUTH_TOKEN_URL, data=payload, headers=headers
        )
        if response.status_code != HTTPStatus.OK:
            raise exceptions.Oauth2Error(response.reason)
        token_info = response.json()
        return token_info

    def _add_custom_values_to_token_info(self, token_info):
        """
        Store some values that aren't directly provided by a Web API
        response.
        """
        token_info["expires_at"] = int(time.time()) + token_info["expires_in"]
        return token_info


class SpotifyOAuth(object):
    """
    Implements Authorization Code Flow for Spotify's OAuth implementation.
    """

    OAUTH_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
    OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Union[str, Sequence[str]],
        state=None,
        cache_path=None,
        session=None,
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

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.state = state
        self.cache_path = cache_path
        if isinstance(scopes, str):
            self.scopes = scopes.split(" ")
        else:
            self.scopes = scopes
        if not session:
            self.session = requests.Session()

    def get_cached_token(self):
        """ Gets a cached auth token
        """
        token_info = None
        if self.cache_path:
            try:
                with open(self.cache_path) as f:
                    token_info = json.load(f)

                # if scopes don't match, then bail
                if "scopes" not in token_info or not set(self.scopes).issubset(
                    token_info["scopes"]
                ):
                    return None

                if is_token_expired(token_info):
                    token_info = self.refresh_access_token(token_info["refresh_token"])
            except IOError:
                pass
        return token_info

    def _save_token_info(self, token_info):
        if self.cache_path:
            try:
                with open(self.cache_path, "w") as f:
                    json.dump(token_info, f)
            except IOError:
                _logger.warning("couldn't write token cache to %s", self.cache_path)
                pass

    def get_authorize_url(self, state=None, show_dialog=False):
        """
        Gets the URL to use to authorize this app
        """
        payload = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state or self.state,
            "show_dialog": show_dialog,
        }
        return "{}?{}".format(self.OAUTH_AUTHORIZE_URL, parse.urlencode(payload))

    def parse_response_code(self, url):
        """ Parse the response code in the given response url

            Parameters:
                - url - the response url
        """

        try:
            return url.split("?code=")[1].split("&")[0]
        except IndexError:
            return None

    def _make_authorization_headers(self):
        return _make_authorization_headers(self.client_id, self.client_secret)

    def get_access_token(self, code):
        """ Gets the access token for the app given the code

            Parameters:
                - code - the response code
        """

        payload = {
            "redirect_uri": self.redirect_uri,
            "code": code,
            "grant_type": "authorization_code",
            "scope": " ".join(self.scopes),
            "state": self.state,
        }

        headers = self._make_authorization_headers()

        response = self.session.post(
            self.OAUTH_TOKEN_URL, data=payload, headers=headers
        )
        if response.status_code != HTTPStatus.OK:
            raise exceptions.Oauth2Error(response.reason)
        token_info = response.json()
        token_info = self._add_custom_values_to_token_info(token_info)
        self._save_token_info(token_info)
        return token_info

    def refresh_access_token(self, refresh_token):
        payload = {"refresh_token": refresh_token, "grant_type": "refresh_token"}

        headers = self._make_authorization_headers()

        response = self.session.post(
            self.OAUTH_TOKEN_URL, data=payload, headers=headers
        )
        if response.status_code != HTTPStatus.OK:
            _logger.warning(
                "couldn't refresh token: code: %d reason:%s",
                response.status_code,
                response.reason,
            )
            return None
        token_info = response.json()
        token_info = self._add_custom_values_to_token_info(token_info)
        if "refresh_token" not in token_info:
            token_info["refresh_token"] = refresh_token
        self._save_token_info(token_info)
        return token_info

    def _add_custom_values_to_token_info(self, token_info: dict):
        """
        Store some values that aren't directly provided by a Web API
        response.
        """
        token_info["expires_at"] = int(time.time()) + token_info["expires_in"]
        token_info["scopes"] = self.scopes
        return token_info
