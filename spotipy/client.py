from http import HTTPStatus
from typing import List
from typing import Sequence
from typing import Tuple
from typing import Union

import requests
import requests.adapters
from urllib3.util import retry

from spotipy import exceptions
from spotipy import params_encoder

""" A simple and thin Python library for the Spotify Web API
"""


def _quota_search_term(term: str):
    if ":" not in term:
        return '"{}"'.format(term) if " " in term else term

    parts = term.split(":", maxsplit=1)
    if " " in parts[1]:
        return '{}:"{}"'.format(*parts)
    return term


def _assert_limit(limit_value, max_limit=50):
    if limit_value is not None:
        if not isinstance(limit_value, int):
            raise TypeError("limit must be int")
        if limit_value < 0 or limit_value > max_limit:
            raise ValueError("limit must be between 1 and 50")


def _assert_offset(offset, assert_max=True):
    if offset:
        if offset < 0:
            raise ValueError("offset can't be a negative number")
        elif assert_max and offset > 100000:
            raise ValueError("offset can't be a greater than 100000")


def _assert_ids_length(ids: Sequence, parameter_name: str, max_length=50):
    if len(ids) > max_length or len(ids) < 0:
        raise ValueError("{} cannot be greater than 50".format(parameter_name))


def _get_id(spotify_type: str, spotify_id: str):
    fields = spotify_id.split(":", maxsplit=2)
    if len(fields) == 3:
        if spotify_type != fields[-2]:
            raise ValueError("expected id of type {} but found type {} {}".format(spotify_type, fields[-2], spotify_id))
        return fields[-1]
    fields = spotify_id.split("/", maxsplit=2)
    if len(fields) == 3:
        itype = fields[-2]
        if spotify_type != itype:
            raise ValueError("expected id of type {} but found type {} {}".format(spotify_type, itype, spotify_id))
        return fields[-1]
    return spotify_id


def _get_uri(spotify_type: str, spotify_id: str):
    return "spotify:{}:{}".format(spotify_type, _get_id(spotify_type, spotify_id))


class Spotify(object):
    """
        Example usage::

            import spotipy

                urn = 'spotify:artist:3jOstUTkEu2JkjvRdBA5Gu'
            sp = spotipy.Spotify()

            sp.trace = True # turn on tracing
            sp.trace_out = True # turn on trace out

            artist = sp.artist(urn)
            print(artist)

            user = sp.user('plamere')
            print(user)
    """

    max_retries = 10

    def __init__(
        self,
        auth=None,
        client_credentials_manager=None,
        requests_session: requests.Session = None,
        default_timeout: Union[int, Tuple[int, int]] = None,
    ):
        """
        Create a Spotify API object.

        :param auth: An authorization token (optional)
        :param requests_session:
            A Requests session object or a truthy value to create one.
            A falsy value disables sessions.
            It should generally be a good idea to keep sessions enabled
            for performance reasons (connection pooling).
        :param client_credentials_manager:
            SpotifyClientCredentials object
        :param default_timeout:
            Tell Requests to stop waiting for a response after a given number of seconds
        """
        self.prefix = "https://api.spotify.com/v1/"
        self._auth = auth
        self.client_credentials_manager = client_credentials_manager
        self.timeout = default_timeout
        if requests_session:
            self._session = requests_session
        else:
            self._session = requests.Session()

        rate_limit_retry = retry.Retry(self.max_retries, read=False, method_whitelist=["POST", "GET", "PUT", "DELETE"])
        self._session.mount("https://", requests.adapters.HTTPAdapter(max_retries=rate_limit_retry))

    def _auth_headers(self):
        if self._auth:
            return {"Authorization": "Bearer {0}".format(self._auth)}
        elif self.client_credentials_manager:
            token = self.client_credentials_manager.get_access_token()
            return {"Authorization": "Bearer {0}".format(token)}
        else:
            return {}

    def _internal_call(self, method: str, url: str, params: dict = None, payload: dict = None):
        if params:
            params = params_encoder.encode_params(params)
        if not url.startswith("http"):
            url = self.prefix + url
        headers = self._auth_headers()

        response = self._session.request(method, url, params, headers=headers, json=payload, timeout=self.timeout)
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            raise exceptions.RateLimitReached(response.headers.get("Retry-After"))

        if 400 <= response.status_code < 500:
            if response.content:
                error = response.json()["error"]
                if (
                    response.status_code == HTTPStatus.NOT_FOUND
                    and "device_id" in params
                    or error.get("reason") == "NO_ACTIVE_DEVICE"
                ):
                    raise exceptions.DeviceNotFoundError(error["message"])
                raise exceptions.SpotifyRequestError(response.status_code, error["message"])
            raise exceptions.SpotifyRequestError(response.status_code, "")

        response.raise_for_status()

        if response.status_code == HTTPStatus.NO_CONTENT:
            return None
        if response.content:
            return response.json()

    def _get(self, url: str, **params):
        return self._internal_call("GET", url, params)

    def _post(self, url: str, payload: dict = None, **params):
        return self._internal_call("POST", url, params, payload)

    def _delete(self, url: str, payload: dict = None, **params):
        return self._internal_call("DELETE", url, params, payload)

    def _put(self, url: str, payload: dict = None, **params):
        return self._internal_call("PUT", url, params, payload)

    def next(self, result):
        """ returns the next result given a paged result

            Parameters:
                - result - a previously returned paged result
        """
        if result["next"]:
            return self._get(result["next"])
        else:
            return None

    def previous(self, result):
        """ returns the previous result given a paged result

            Parameters:
                - result - a previously returned paged result
        """
        if result["previous"]:
            return self._get(result["previous"])
        else:
            return None

    def track(self, track_id: str, market: str = None) -> dict:
        """ Get Spotify catalog information for a single track.

            Parameters:
                - track_id - a spotify URI, URL or ID.
        """

        return self._get("tracks/" + _get_id("track", track_id), market=market)

    def tracks(self, tracks: Sequence[str], market: str = None) -> List[dict]:
        """ Get Spotify catalog information for multiple tracks.

            Parameters:
                - tracks - a list of spotify IDs, URIs or URLs. Maximum items: 50.
                - market - An ISO 3166-1 alpha-2 country code or the string from_token.
        """
        _assert_ids_length(tracks, "tracks")

        return self._get("tracks/", ids=[_get_id("track", track) for track in tracks], market=market)["tracks"]

    def track_audio_analysis(self, track_id: str) -> dict:
        """ Get a detailed audio analysis for a single track

            The Audio Analysis endpoint provides low-level audio analysis for all of the tracks in the Spotify catalog.
            The Audio Analysis describes the track's structure and musical content, including rhythm, pitch, and timbre.
            All information is precise to the audio sample. Many elements of analysis include confidence values,
            a floating-point number ranging from 0.0 to 1.0.

            Confidence indicates the reliability of its corresponding attribute.
            Elements carrying a small confidence value should be considered speculative.
            There may not be sufficient data in the audio to compute the attribute with high certainty.

            Parameters:
                - track_id - a spotify ID, URI or URL.
        """

        return self._get("audio-analysis/" + _get_id("track", track_id))

    def track_audio_feature(self, track_id: str) -> dict:
        """ Get audio feature information for a single track.

            Parameters:
                - track_id - a spotify ID, URI or URL.
        """

        return self._get("audio-features/{}".format(_get_id("track", track_id)))

    def tracks_audio_feature(self, tracks: Sequence[str]) -> List[dict]:
        """ Get audio features for multiple tracks.

            Parameters:
                - tracks - a list of spotify IDs, URIs or URLs. Maximum items: 50.
        """
        _assert_ids_length(tracks, "tracks")

        return self._get("audio-features", ids=[_get_id("track", track) for track in tracks])["audio_features"]

    def artist(self, artist_id: str) -> dict:
        """ Get Spotify catalog information for a single artist.

            Parameters:
                - artist_id - an artist ID, URI or URL.
        """

        artist_id = _get_id("artist", artist_id)
        return self._get("artists/" + artist_id)

    def artists(self, artists: List[str]) -> List[dict]:
        """ Get Spotify catalog information for several artists.

            Parameters:
                - artists - a list of  artist IDs, URIs or URLs.
        """
        _assert_ids_length(artists, "artists")
        return self._get("artists/", ids=[_get_id("artist", artists) for artists in artists])["artists"]

    def artist_albums(
        self,
        artist_id: str,
        include_groups: Union[str, Sequence[str]] = None,
        market: str = None,
        limit: int = None,
        offset: int = None,
    ):
        """ Get Spotify catalog information about an artist's albums

            Parameters:
                - artist_id - the artist ID, URI or URL
                - include_groups - 'album', 'single', 'appears_on', 'compilation'
                - market - An ISO 3166-1 alpha-2 country code or the string from_token.
                - limit - The number of album objects to return. Default: 20. Minimum: 1. Maximum: 50.
                - offset - The index of the first album to return. Default: 0.
        """
        _assert_limit(limit)
        _assert_offset(offset)
        return self._get(
            "artists/{}/albums".format(_get_id("artist", artist_id)),
            include_groups=include_groups,
            market=market,
            limit=limit,
            offset=offset,
        )

    def artist_top_tracks(self, artist_id: str, market="from_token"):
        """ Get Spotify catalog information about an artist's top tracks by country.

            Parameters:
                - artist_id - the artist ID, URI or URL
                - market - An ISO 3166-1 alpha-2 country code or the string from_token.
        """

        return self._get("artists/{}/top-tracks".format(_get_id("artist", artist_id)), market=market)

    def artist_related_artists(self, artist_id: str):
        """ Get Spotify catalog information about artists similar to a given artist.
        Similarity is based on analysis of the Spotify community's listening history.

            Parameters:
                - artist_id - the artist ID, URI or URL
        """
        return self._get("artists/{}/related-artists".format(_get_id("artist", artist_id)))

    def album(self, album_id: str) -> dict:
        """ Get Spotify catalog information for a single album.

            Parameters:
                - album_id - the album ID, URI or URL
        """

        album_id = _get_id("album", album_id)
        return self._get("albums/" + album_id)

    def album_tracks(self, album_id: str, limit: int = None, offset: int = None):
        """ Get Spotify catalog information about an album's tracks

            Parameters:
                - album_id - the album ID, URI or URL
                - limit - The maximum number of tracks to return. Default: 20. Minimum: 1. Maximum: 50.
                - offset - The index of the first track to return. Default: 0 (the first object).
                Use with limit to get the next set of tracks.
        """
        _assert_limit(limit)
        _assert_offset(offset)
        return self._get("albums/{}/tracks".format(_get_id("album", album_id)), limit=limit, offset=offset)

    def albums(self, albums: Sequence[str]) -> List[dict]:
        """ Get Spotify catalog information for multiple albums

            Parameters:
                - albums - a list of  album IDs, URIs or URLs
        """

        _assert_ids_length(albums, "albums", 20)
        return self._get("albums/", ids=[_get_id("album", album) for album in albums])["albums"]

    def search(
        self,
        q: str,
        item_type: Union[str, Sequence[str]],
        limit: int = None,
        offset: int = None,
        market: str = None,
        include_external_audio=False,
    ):
        """ searches for an item

            Parameters:
                - q - the search query, see https://developer.spotify.com/documentation/web-api/reference/search/search/#writing-a-query---guidelines
                - type - a list of type item to return or string which is one of 'artist', 'album', 'track' or 'playlist'
                - limit  - the number of items to return
                - offset - the index of the first item to return
                - market - An ISO 3166-1 alpha-2 country code or the string from_token.
                - include_external - if true, the response will include any relevant audio content that is hosted externally
        """
        if isinstance(item_type, str) and item_type not in ("artist", "album", "track", "playlist"):
            raise ValueError("item_type must be one of 'artist', 'album', 'track' or 'playlist'")
        else:
            for type_ in item_type:
                if type_ not in ("artist", "album", "track", "playlist"):
                    raise ValueError("item_type must be one of 'artist', 'album', 'track' or 'playlist'")
        _assert_limit(limit)
        _assert_offset(offset)
        params = {"q": q, "limit": limit, "offset": offset, "type": item_type, "market": market}
        if include_external_audio:
            params["include_external"] = "audio"
        return self._get("search", **params)

    def search2(
        self,
        keywords: Sequence[str],
        item_type: Union[str, Sequence[str]],
        excludes: Sequence[str] = None,
        optional: str = None,
        limit: int = None,
        offset: int = None,
        market: str = None,
        include_external_audio=False,
    ) -> dict:
        """ searches for an item
        see https://developer.spotify.com/documentation/web-api/reference/search/search/#writing-a-query---guidelines
        for more details

            Parameters:
                - keywords - keywords to search
                - excludes - keywords to exclude in search
                - optional: one keyword as an OR operator
                - type - a list of type item to return or string which is one of 'artist', 'album', 'track' or 'playlist'
                - limit  - the number of items to return
                - offset - the index of the first item to return
                - market - An ISO 3166-1 alpha-2 country code or the string from_token.
                - include_external - if true, the response will include any relevant audio content that is hosted externally
        """
        if isinstance(item_type, str) and item_type not in ("artist", "album", "track", "playlist"):
            raise ValueError("item_type must be one of 'artist', 'album', 'track' or 'playlist'")
        else:
            for type_ in item_type:
                if type_ not in ("artist", "album", "track", "playlist"):
                    raise ValueError("item_type must be one of 'artist', 'album', 'track' or 'playlist'")
        _assert_limit(limit)
        _assert_offset(offset)
        parts = []
        if keywords:
            parts.append(" ".join(_quota_search_term(keyword) for keyword in keywords))
        if excludes:
            parts.append(" NOT " + " NOT ".join(_quota_search_term(exclude) for exclude in excludes))
        if optional:
            parts.append(" OR " + _quota_search_term(optional))

        params = {"q": " ".join(parts), "limit": limit, "offset": offset, "type": item_type, "market": market}
        if include_external_audio:
            params["include_external"] = "audio"
        return self._get("search", **params)

    def user(self, user_id: str) -> dict:
        """ Get public profile information about a Spotify user.

            Parameters:
                - user_id - the id of the usr
        """
        return self._get("users/" + _get_id("user", user_id))

    def current_user_playlists(self, limit: int = None, offset: int = None) -> dict:
        """ Get a list of the playlists owned or followed by the current Spotify user.
            Parameters:
                - limit - The maximum number of playlist to return. Default: 20. Minimum: 1. Maximum: 50.
                - offset - The index of the first playlist to return. Default: 0. Maximum offset: 100,000.
        """
        _assert_limit(limit)
        _assert_offset(offset)

        return self._get("me/playlists", limit=limit, offset=offset)

    def user_playlists(self, user_id: str, limit: int = None, offset: int = None) -> dict:
        """ Gets playlists of a user

            Parameters:
                - user_id - the id of the usr
                - limit - The maximum number of playlists to return. Default: 20. Minimum: 1. Maximum: 50.
                - offset - The index of the first playlist to return. Default: 0. Maximum offset: 100,000.
        """
        _assert_limit(limit)
        _assert_offset(offset)
        return self._get("users/{}/playlists".format(_get_id("user", user_id)), limit=limit, offset=offset)

    def playlist(self, playlist_id: str, fields: str = None, market: str = None) -> dict:
        """ Get a playlist owned by a Spotify user

            Parameters:
                - playlist_id - the id of the playlist
                - fields - which fields to return, see https://developer.spotify.com/documentation/web-api/reference/playlists/get-playlist/
        """
        return self._get("playlists/" + _get_id("playlist", playlist_id), fields=fields, market=market)

    def playlist_tracks(
        self, playlist_id: str, fields: str = None, limit: int = None, offset: int = None, market: str = None
    ) -> dict:
        """ Get full details of the tracks of a playlist owned by a user.

            Parameters:
                - playlist_id - the id of the playlist.
                - fields - which fields to return. see https://developer.spotify.com/documentation/web-api/reference/playlists/get-playlists-tracks/
                - limit - The maximum number of tracks to return. Default: 100. Minimum: 1. Maximum: 100.
                - offset - The index of the first track to return. Default: 0.
                - market - An ISO 3166-1 alpha-2 country code or the string from_token.
        """
        _assert_limit(limit, 100)
        _assert_offset(offset)
        url = "playlists/{}/tracks".format(_get_id("playlist", playlist_id))
        return self._get(url, limit=limit, offset=offset, fields=fields, market=market)

    def user_playlist_create(
        self, user_id: str, name: str, public: bool = None, collaborative: bool = None, description: str = None
    ) -> dict:
        """ Create a playlist for a Spotify user

            Parameters:
                - user_id - the id of the user
                - name - the name of the playlist
                - public - is the created playlist public
                - description - the description of the playlist
        """
        payload = {"name": name}
        if public is not None:
            payload["public"] = public
        if collaborative is not None:
            payload["collaborative"] = collaborative
        if description:
            payload["description"] = description
        return self._post("users/{}/playlists".format(_get_id("user", user_id)), payload)

    def playlist_change_details(
        self,
        playlist_id: str,
        name: str = None,
        public: bool = None,
        collaborative: bool = None,
        description: str = None,
    ) -> None:
        """ Change a playlist’s name and public/private state.

            Parameters:
                - playlist_id - the id of the playlist
                - name - optional name of the playlist
                - public - optional is the playlist public
                - collaborative - optional is the playlist collaborative
                - description - optional description of the playlist
        """

        payload = {}
        if name:
            if not isinstance(name, str):
                raise ValueError("name must be string")
            payload["name"] = name
        if public is not None:
            if not isinstance(public, bool):
                raise ValueError("public must be boolean")
            payload["public"] = public
        if collaborative is not None:
            if not isinstance(collaborative, bool):
                raise ValueError("collaborative must be boolean")
            payload["collaborative"] = collaborative
        if description:
            if not isinstance(description, str):
                raise ValueError("description must be string")
            payload["description"] = description
        return self._put("playlists/{}".format(playlist_id), payload)

    def playlist_unfollow(self, playlist_id: str) -> None:
        """ Remove the current user as a follower of a playlist

            Parameters:
                - playlist_id - the name of the playlist
        """
        return self._delete("playlists/{}/followers".format(playlist_id))

    def playlist_add_tracks(self, playlist_id: str, tracks: Sequence[str], position: int = None) -> str:
        """ Add one or more tracks to a user’s playlist.

            Parameters:
                - playlist_id - the id of the playlist
                - tracks - a list of spotify IDs, URIs or URLs. Maximum items: 100.
                - position - the position to add the tracks in the list
        """
        _assert_ids_length(tracks, "track", 100)
        payload = {"uris": [_get_uri("track", track_id) for track_id in tracks]}
        if position is not None:
            payload["position"] = position
        url = "playlists/{}/tracks".format(_get_id("playlist", playlist_id))
        return self._post(url, payload)["snapshot_id"]

    def playlist_replace_tracks(self, playlist_id: str, tracks: List[str]) -> str:
        """ Replace all the tracks in a playlist, overwriting its existing tracks.

            Parameters:
                - user - the id of the user
                - playlist_id - the id of the playlist
                - tracks - a list of spotify IDs, URIs or URLs. Maximum items: 100.
        """
        _assert_ids_length(tracks, "tracks", 100)
        payload = {"uris": [_get_uri("track", track) for track in tracks]}
        return self._put("playlists/{}/tracks".format(_get_id("playlist", playlist_id)), payload)["snapshot_id"]

    def playlist_reorder_tracks(
        self, playlist_id: str, range_start: int, insert_before: int, range_length: int = None, snapshot_id: str = None
    ):
        """ Reorder a track or a group of tracks in a playlist.

            Parameters:
                - playlist_id - the id of the playlist
                - range_start - the position of the first track to be reordered
                - range_length - optional the number of tracks to be reordered (default: 1)
                - insert_before - the position where the tracks should be inserted
                - snapshot_id - optional playlist's snapshot ID
        """
        payload = {"range_start": range_start, "insert_before": insert_before}
        if snapshot_id:
            payload["snapshot_id"] = snapshot_id
        if range_length is not None:
            payload["range_length"] = range_length
        return self._put("playlists/{}/tracks".format(_get_id("playlist", playlist_id)), payload)["snapshot_id"]

    def playlist_remove_all_occurrences_of_tracks(
        self, playlist_id: str, tracks: Sequence[str], snapshot_id: str = None
    ) -> str:
        """ Removes all occurrences of the given tracks from the given playlist

            Parameters:
                - playlist_id - the id of the playlist
                - tracks - a list of spotify IDs, URIs or URLs. Maximum items: 100.
                - snapshot_id - optional id of the playlist snapshot

        """
        _assert_ids_length(tracks, "tracks", 100)
        payload = {"tracks": [{"uri": _get_uri("track", track)} for track in tracks]}
        if snapshot_id:
            payload["snapshot_id"] = snapshot_id
        return self._delete("playlists/{}/tracks".format(_get_id("playlist", playlist_id)), payload)["snapshot_id"]

    def playlist_remove_specific_occurrences_of_tracks(
        self, playlist_id: str, tracks: Sequence[dict], snapshot_id: str = None
    ) -> str:
        """ Removes specific occurrences of the given tracks from the given playlist

            Parameters:
                - playlist_id - the id of the playlist
                - tracks - an array of objects containing Spotify URIs of the tracks to remove with their current
                 positions in the playlist. For example:
                    [  { "uri":"4iV5W9uYEdYUVa79Axb7Rh", "positions":[2] },
                       { "uri":"1301WleyT98MSxVHPZCA6M", "positions":[7] } ]. Maximum: 100.
                - snapshot_id - optional id of the playlist snapshot
        """
        _assert_ids_length(tracks, "tracks", 100)
        payload = {
            "tracks": [{"uri": _get_uri("track", track["uri"]), "positions": track["positions"]} for track in tracks]
        }

        if snapshot_id:
            payload["snapshot_id"] = snapshot_id
        return self._delete("playlists/{}/tracks".format(_get_id("playlist", playlist_id)), payload)["snapshot_id"]

    def follow_playlist(self, playlist_id: str) -> None:
        """
        Add the current user as a follower of a playlist.

        Parameters:
            - playlist_id - the id of the playlist

        """
        return self._put("playlists/{}/followers".format(playlist_id))

    def is_users_follow_playlist(self, playlist_id: str, users: Sequence[str]) -> bool:
        """
        Check to see if the given users are following the given playlist

        Parameters:
            - playlist_id - the id of the playlist
            - users - the ids of the users that you want to check to see if they follow the playlist. Maximum: 5 ids.

        """
        _assert_ids_length(users, "users", 5)
        return self._get("playlists/{}/followers/contains".format(_get_id("playlist", playlist_id)), ids=users)[0]

    def me(self) -> dict:
        """ Get detailed profile information about the current user.
            An alias for the 'current_user' method.
        """
        return self._get("me")

    def current_user(self) -> dict:
        """ Get detailed profile information about the current user.
            An alias for the 'me' method.
        """
        return self.me()

    def current_user_playing_track(self) -> dict:
        """ Get the object currently being played on the user’s Spotify account.
        """
        return self._get("me/player/currently-playing")

    def current_user_saved_albums(self, limit=600, offset=0):
        """ Gets a list of the albums saved in the current authorized user's
            "Your Music" library

            Parameters:
                - limit - the number of albums to return
                - offset - the index of the first album to return

        """
        return self._get("me/albums", limit=limit, offset=offset)

    def current_user_saved_tracks(self, limit=20, offset=0):
        """ Gets a list of the tracks saved in the current authorized user's
            "Your Music" library

            Parameters:
                - limit - the number of tracks to return
                - offset - the index of the first track to return

        """
        return self._get("me/tracks", limit=limit, offset=offset)

    def current_user_followed_artists(self, limit: int = None, after_artist: str = None):
        """ Get the current user's followed artists.

            Parameters:
                - limit - The maximum number of items to return. Default: 20. Minimum: 1. Maximum: 50
                - after_artist - The last artist ID retrieved from the previous request.

        """
        _assert_limit(limit)

        return self._get("me/following", type="artist", limit=limit, after=_get_id("artists", after_artist))

    def is_current_user_following_artists(self, artists: Sequence[str]) -> bool:
        """ Check to see if the current user is following one or more artists or other Spotify users.

            Parameters:
                - artists - a list of artist IDs, URIs or URLs

        """
        if isinstance(artists, str):
            raise ValueError("artists must be a sequence of strings")

        if len(artists) > 50 or len(artists) < 0:
            raise ValueError("artists cannot be larger than 50")

        response = self._get(
            "me/following/contains", type="artist", ids=[_get_id("artist", artist) for artist in artists]
        )
        return response[0]

    def is_current_user_following_users(self, users: Sequence[str]) -> bool:
        """ Check to see if the current user is following one or more artists or other Spotify users.

            Parameters:
                - users - a list of user IDs

        """
        if isinstance(users, str):
            raise ValueError("users must be a list")

        if len(users) > 50 or len(users) < 0:
            raise ValueError("users cannot be larger than 50")

        return self._get("me/following/contains", type="user", ids=[_get_id("user", user) for user in users])[0]

    def current_user_saved_tracks_delete(self, tracks=None):
        """ Remove one or more tracks from the current user's
            "Your Music" library.

            Parameters:
                - tracks - a list of track URIs, URLs or IDs
        """
        tlist = []
        if tracks is not None:
            tlist = [_get_id("track", t) for t in tracks]
        return self._delete("me/tracks/?ids=" + ",".join(tlist))

    def current_user_saved_tracks_contains(self, tracks=None):
        """ Check if one or more tracks is already saved in
            the current Spotify user's “Your Music” library.

            Parameters:
                - tracks - a list of track URIs, URLs or IDs
        """
        tlist = []
        if tracks is not None:
            tlist = [_get_id("track", t) for t in tracks]
        return self._get("me/tracks/contains?ids=" + ",".join(tlist))

    def current_user_saved_tracks_add(self, tracks=None):
        """ Add one or more tracks to the current user's
            "Your Music" library.

            Parameters:
                - tracks - a list of track URIs, URLs or IDs
        """
        tlist = []
        if tracks is not None:
            tlist = [_get_id("track", t) for t in tracks]
        return self._put("me/tracks/?ids=" + ",".join(tlist))

    def current_user_top_artists(self, limit: int = None, offset: int = None, time_range: str = None):
        """ Get the current user's top artists

            Parameters:
                - limit - The number of artists to return. Default: 20. Minimum: 1. Maximum: 50
                - offset - The index of the first artist to return. Default: 0.
                - time_range - Over what time frame are the affinities computed
                  Valid-values: short_term, medium_term, long_term
        """
        _assert_limit(limit)
        if time_range and time_range not in ("short_term", "medium_term", "long_term"):
            raise ValueError("time_range can be one of short_term, medium_term, long_term")

        return self._get("me/top/artists", time_range=time_range, limit=limit, offset=offset)

    def current_user_top_tracks(self, limit: int = None, offset: int = None, time_range: str = None):
        """ Get the current user's top tracks

            Parameters:
                - limit - The number of tracks to return. Default: 20. Minimum: 1. Maximum: 50
                - offset - The index of the first track to return. Default: 0.
                - time_range - Over what time frame are the affinities computed
                  Valid-values: short_term, medium_term, long_term
        """
        _assert_limit(limit)
        if time_range and time_range not in ("short_term", "medium_term", "long_term"):
            raise ValueError("time_range can be one of short_term, medium_term, long_term")

        return self._get("me/top/tracks", time_range=time_range, limit=limit, offset=offset)

    def current_user_recently_played(self, limit=None, before=None, after=None):
        """ Get the current user's recently played tracks

            Parameters:
                - limit - The maximum number of items to return. Default: 20. Minimum: 1. Maximum: 50.
        """
        _assert_limit(limit)
        if before and after:
            raise ValueError("before and after can't be set together")
        return self._get("me/player/recently-played", limit=limit, before=before, after=after)

    def current_user_saved_albums_delete(self, albums: List[str]):
        """ Remove one or more albums from the current user's
            "Your Music" library.

            Parameters:
                - albums - a list of album URIs, URLs or IDs
        """
        alist = [_get_id("album", album) for album in albums]
        r = self._delete("me/albums/?ids=" + ",".join(alist))
        return r

    def current_user_saved_albums_contains(self, albums):
        """ Check if one or more albums is already saved in
            the current Spotify user's “Your Music” library.

            Parameters:
                - albums - a list of album URIs, URLs or IDs
        """
        alist = [_get_id("album", a) for a in albums]
        r = self._get("me/albums/contains?ids=" + ",".join(alist))
        return r

    def current_user_saved_albums_add(self, albums):
        """ Add one or more albums to the current user's
            "Your Music" library.
            Parameters:
                - albums - a list of album URIs, URLs or IDs
        """
        alist = [_get_id("album", a) for a in albums]
        r = self._put("me/albums?ids=" + ",".join(alist))
        return r

    def follow_artists(self, artists: Sequence[str]):
        """ Follow one or more artists
            Parameters:
                - artists - a list of artist IDs, URIs or URLs or single artist ID, URI or URL
        """
        if isinstance(artists, str):
            raise ValueError("artists must be a list")

        if len(artists) > 50 or len(artists) < 0:
            raise ValueError("artists cannot be larger than 50")

        return self._put("me/following", type="artist", ids=[_get_id("artist", artist) for artist in artists])

    def follow_users(self, users: Sequence[str]):
        """ Follow one or more users
            Parameters:
                - users - a list of user IDs
        """
        if isinstance(users, str):
            raise ValueError("users must be a list")

        if len(users) > 50 or len(users) < 0:
            raise ValueError("users cannot be larger than 50")

        return self._put("me/following", type="user", ids=[_get_id("user", user) for user in users])

    def unfollow_artists(self, artists: Sequence[str]):
        """ Unfollow one or more artists
            Parameters:
                - artists - a list of artist IDs, URIs or URLs
        """
        if isinstance(artists, str):
            raise ValueError("artists must be a list")

        if len(artists) > 50 or len(artists) < 0:
            raise ValueError("artists cannot be larger than 50")

        return self._delete("me/following", type="artist", ids=[_get_id("artist", artist) for artist in artists])

    def unfollow_users(self, users: Sequence[str]):
        """ Unfollow one or more users
            Parameters:
                - users - a list of user IDs
        """
        if isinstance(users, str):
            raise ValueError("users must be a list")

        if len(users) > 50 or len(users) < 0:
            raise ValueError("users cannot be larger than 50")

        return self._delete("me/following", type="user", ids=[_get_id("user", user) for user in users])

    def featured_playlists(self, locale=None, country=None, timestamp=None, limit=20, offset=0):
        """ Get a list of Spotify featured playlists

            Parameters:
                - locale - The desired language, consisting of a lowercase ISO
                  639 language code and an uppercase ISO 3166-1 alpha-2 country
                  code, joined by an underscore.

                - country - An ISO 3166-1 alpha-2 country code.

                - timestamp - A timestamp in ISO 8601 format:
                  yyyy-MM-ddTHH:mm:ss. Use this parameter to specify the user's
                  local time to get results tailored for that specific date and
                  time in the day

                - limit - The maximum number of items to return. Default: 20. Minimum: 1. Maximum: 50

                - offset - The index of the first item to return. Default: 0
                  (the first object). Use with limit to get the next set of
                  items.
        """
        return self._get(
            "browse/featured-playlists", locale=locale, country=country, timestamp=timestamp, limit=limit, offset=offset
        )

    def new_releases(self, country=None, limit=20, offset=0):
        """ Get a list of new album releases featured in Spotify

            Parameters:
                - country - An ISO 3166-1 alpha-2 country code.

                - limit - The maximum number of items to return. Default: 20. Minimum: 1. Maximum: 50

                - offset - The index of the first item to return. Default: 0
                  (the first object). Use with limit to get the next set of
                  items.
        """
        return self._get("browse/new-releases", country=country, limit=limit, offset=offset)

    def categories(self, country=None, locale=None, limit=20, offset=0):
        """ Get a list of new album releases featured in Spotify

            Parameters:
                - country - An ISO 3166-1 alpha-2 country code.
                - locale - The desired language, consisting of an ISO 639
                  language code and an ISO 3166-1 alpha-2 country code, joined
                  by an underscore.

                - limit - The maximum number of items to return. Default: 20. Minimum: 1. Maximum: 50

                - offset - The index of the first item to return. Default: 0
                  (the first object). Use with limit to get the next set of
                  items.
        """
        return self._get("browse/categories", country=country, locale=locale, limit=limit, offset=offset)

    def category_playlists(self, category_id=None, country=None, limit=20, offset=0):
        """ Get a list of new album releases featured in Spotify

            Parameters:
                - category_id - The Spotify category ID for the category.

                - country - An ISO 3166-1 alpha-2 country code.

                - limit - The maximum number of items to return. Default: 20. Minimum: 1. Maximum: 50

                - offset - The index of the first item to return. Default: 0
                  (the first object). Use with limit to get the next set of
                  items.
        """
        return self._get("browse/categories/" + category_id + "/playlists", country=country, limit=limit, offset=offset)

    def recommendations(self, seed_artists=None, seed_genres=None, seed_tracks=None, limit=20, country=None, **kwargs):
        """ Get a list of recommended tracks for one to five seeds.

            Parameters:
                - seed_artists - a list of artist IDs, URIs or URLs
                - seed_tracks - a list of artist IDs, URIs or URLs

                - seed_genres - a list of genre names. Available genres for
                  recommendations can be found by calling recommendation_genre_seeds

                - country - An ISO 3166-1 alpha-2 country code. If provided, all
                  results will be playable in this country.

                - limit - The maximum number of items to return. Default: 20. Minimum: 1. Maximum: 100

                - min/max/target_<attribute> - For the tunable track attributes listed
                  in the documentation, these values provide filters and targeting on
                  results.
        """
        params = dict(limit=limit)
        if seed_artists:
            params["seed_artists"] = ",".join([_get_id("artist", a) for a in seed_artists])
        if seed_genres:
            params["seed_genres"] = ",".join(seed_genres)
        if seed_tracks:
            params["seed_tracks"] = ",".join([_get_id("track", t) for t in seed_tracks])
        if country:
            params["market"] = country

        for attribute in [
            "acousticness",
            "danceability",
            "duration_ms",
            "energy",
            "instrumentalness",
            "key",
            "liveness",
            "loudness",
            "mode",
            "popularity",
            "speechiness",
            "tempo",
            "time_signature",
            "valence",
        ]:
            for prefix in ["min_", "max_", "target_"]:
                param = prefix + attribute
                if param in kwargs:
                    params[param] = kwargs[param]
        return self._get("recommendations", **params)

    def recommendation_genre_seeds(self):
        """ Get a list of genres available for the recommendations function.
        """
        return self._get("recommendations/available-genre-seeds")

    def devices(self) -> List[dict]:
        """ Get information about a user’s available devices.
        """
        return self._get("me/player/devices")["devices"]

    def current_playback(self, market: str = None) -> dict:
        """ Get information about the user’s current playback state, including track, track progress, and active device.

            Parameters:
                - market - An ISO 3166-1 alpha-2 country code or the string from_token.
        """
        return self._get("me/player", market=market)

    def currently_playing(self, market: str = None) -> dict:
        """ Get user's currently playing track.

            Parameters:
                - market - An ISO 3166-1 alpha-2 country code or the string from_token.
        """
        return self._get("me/player/currently-playing", market=market)

    def transfer_playback(self, device_id: str, force_play: bool = None) -> None:
        """ Transfer playback to a new device and determine if it should start playing.

            Parameters:
                - device_id - transfer playback to this device
                - force_play - true: after transfer, play. false:
                               keep current state.
        """
        payload = {"device_ids": [device_id]}
        if force_play:
            payload["play"] = True
        return self._put("me/player", payload)

    def start_playback(
        self,
        device_id: str = None,
        context_uri: str = None,
        uris: List[str] = None,
        offset: int = None,
        position_ms: int = None,
    ) -> None:
        """ Start a new context or resume current playback on the user’s active device.

            Provide a `context_uri` to start playback or a album,
            artist, or playlist.

            Provide a `uris` list to start playback of one or more
            tracks.

            Provide `offset` as {"position": <int>} or {"uri": "<track uri>"}
            to start playback at a particular offset.

            Parameters:
                - device_id - device target for playback
                - context_uri - spotify context uri to play
                - uris - spotify track uris
                - offset - offset into context by index or track
        """
        if context_uri is not None and uris is not None:
            raise ValueError("specify either context uri or uris, not both")
        if uris is not None and not isinstance(uris, list):
            raise TypeError("uris must be a list")
        if position_ms is not None and not isinstance(position_ms, int):
            raise TypeError("position_ms must be integer")

        payload = {}
        if context_uri is not None:
            payload["context_uri"] = context_uri
        if uris:
            payload["uris"] = [_get_uri("track", uri) for uri in uris]
        if offset is not None:
            payload["offset"] = offset
        if position_ms is not None:
            payload["position_ms"] = position_ms

        return self._put("me/player/play", payload or None, device_id=device_id)

    def pause_playback(self, device_id: str = None) -> None:
        """ Pause playback on the user’s account.

            Parameters:
                - device_id - device target for playback
        """
        return self._put("me/player/pause", device_id=device_id)

    def next_track(self, device_id: str = None) -> None:
        """ Skips to next track in the user’s queue.

            Parameters:
                - device_id - device target for playback
        """
        return self._post("me/player/next", device_id=device_id)

    def previous_track(self, device_id: str = None) -> None:
        """ Skips to previous track in the user’s queue.

            Parameters:
                - device_id - device target for playback
        """
        return self._post("me/player/previous", device_id=device_id)

    def seek_track(self, position_ms: int, device_id: str = None) -> None:
        """ Seeks to the given position in the user’s currently playing track.

            Parameters:
                - position_ms - position in milliseconds to seek to
                - device_id - device target for playback
        """
        if not isinstance(position_ms, int):
            raise TypeError("position_ms must be an integer")
        if position_ms < 0:
            raise ValueError("position_ms cannot be negative")

        return self._put("me/player/seek", position_ms=position_ms, device_id=device_id)

    def repeat(self, state: str, device_id: str = None) -> None:
        """ Set the repeat mode for the user’s playback.

            Parameters:
                - state - `track`, `context`, or `off`
                - device_id - device target for playback
        """
        if state not in ("track", "context", "off"):
            raise ValueError("invalid state")
        self._put("me/player/repeat", state=state, device_id=device_id)

    def volume(self, volume_percent: int, device_id: str = None) -> None:
        """ Set playback volume.

            Parameters:
                - volume_percent - volume between 0 and 100
                - device_id - device target for playback
        """
        if not isinstance(volume_percent, int):
            raise TypeError("volume must be an integer")
        if volume_percent < 0 or volume_percent > 100:
            raise ValueError("volume must be between 0 and 100, inclusive")

        self._put("me/player/volume", volume_percent=volume_percent, device_id=device_id)

    def shuffle(self, state: bool, device_id: str = None) -> None:
        """ Toggle shuffle on or off for user’s playback.

            Parameters:
                - state - true or false
                - device_id - device target for playback
        """
        if not isinstance(state, bool):
            raise TypeError("state must be a boolean")

        self._put("me/player/shuffle", state=state, device_id=device_id)
