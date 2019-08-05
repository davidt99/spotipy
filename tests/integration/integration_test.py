import json
import unittest
from http import HTTPStatus

import spotipy
from spotipy import exceptions


class BaseSpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(".cache") as f:
            token_info = json.load(f)

        cls.token = token_info["access_token"]

    def setUp(self) -> None:
        self.sp = spotipy.Spotify(auth=self.token)


class ErrorSpec(BaseSpec):
    def test_get_invalid_artists_raises_an_exceptions(self):
        # Arrange
        artist_id = "spotify:artist:7zrkMAR1BouState4QYoEg"

        # Act
        with self.assertRaises(exceptions.SpotifyRequestError) as context:
            self.sp.artist(artist_id)

        self.assertEqual(HTTPStatus.NOT_FOUND, context.exception.status)


class AlbumSpec(BaseSpec):
    def test_get_album(self):
        # Arrange
        album_id = "spotify:album:6IH6co1QUS7uXoyPDv0rIr"

        # Act
        album = self.sp.album(album_id)

        # Assert
        self.assertEqual("Jungle", album["name"])
        self.assertEqual(album_id, album["uri"])

    def test_get_album_tracks(self):
        # Arrange
        album_id = "spotify:album:6IH6co1QUS7uXoyPDv0rIr"

        # Act
        tracks = self.sp.album_tracks(album_id)

        # Assert
        self.assertEqual(12, tracks["total"])
        self.assertEqual("The Heat", tracks["items"][0]["name"])

    def test_get_album_tracks_pagination(self):
        # Arrange
        album_id = "spotify:album:70FGsJuLXPQHYdKmEZZFq9"
        limit = 5

        # Act 1
        tracks = self.sp.album_tracks(album_id, limit=limit)

        # Assert 1
        self.assertEqual(limit, tracks["limit"])

        # Act 2
        next_tracks = self.sp.next(tracks)
        expected_tracks = self.sp.album_tracks(album_id, limit, limit)

        # Asset 2
        self.assertEqual(limit, next_tracks["limit"])
        self.assertEqual(limit, next_tracks["offset"])
        self.assertEqual(expected_tracks["href"], next_tracks["href"])

    def test_get_albums(self):
        # Arrange
        albums_id = ["spotify:album:6IH6co1QUS7uXoyPDv0rIr", "spotify:album:7GjVWG39IOj4viyWplJV4H"]

        # Act
        albums = self.sp.albums(albums_id)

        # Assert
        self.assertEqual(len(albums_id), len(albums["albums"]))
        self.assertEqual("Jungle", albums["albums"][0]["name"])
        self.assertEqual("Little Dark Age", albums["albums"][1]["name"])


class ArtistsSpec(BaseSpec):
    def test_get_artist(self):
        # Arrange
        artist_id = "spotify:artist:7zrkALJ9ayRjzysp4QYoEg"

        # Act
        artist = self.sp.artist(artist_id)

        # Assert
        self.assertEqual(artist_id, artist["uri"])
        self.assertEqual("Maribou State", artist["name"])

    def test_get_artists(self):
        # Arrange
        artists_id = ["spotify:artist:7zrkALJ9ayRjzysp4QYoEg", "spotify:artist:2mVVjNmdjXZZDvhgQWiakk"]

        # Act
        artists = self.sp.artists(artists_id)

        # Assert
        self.assertEqual(len(artists_id), len(artists["artists"]))
        self.assertEqual("Maribou State", artists["artists"][0]["name"])
        self.assertEqual("Khruangbin", artists["artists"][1]["name"])

    def test_get_artist_albums(self):
        # Arrange
        artist_id = "spotify:artist:7zrkALJ9ayRjzysp4QYoEg"
        include_groups = ["album", "single"]
        limit = 50

        # Act 1
        albums = self.sp.artist_albums(artist_id, include_groups, limit=limit)

        # Assert 1
        self.assertGreaterEqual(albums["total"], limit)

        # Act 2
        next_albums = self.sp.next(albums)
        expected_albums = self.sp.artist_albums(artist_id, include_groups, limit=limit, offset=limit)

        # Asset 2
        self.assertEqual(limit, next_albums["limit"])
        self.assertEqual(limit, next_albums["offset"])
        self.assertEqual(expected_albums["href"], next_albums["href"])

    def test_get_artist_top_tracks(self):
        # Arrange
        artist_id = "spotify:artist:4pejUc4iciQfgdX6OKulQn"

        # Act
        top_tracks = self.sp.artist_top_tracks(artist_id)

        # Assert
        self.assertEqual(10, len(top_tracks["tracks"]))

    def test_get_artist_related_artists(self):
        # Arrange
        artist_id = "spotify:artist:4pejUc4iciQfgdX6OKulQn"

        # Act
        artists = self.sp.artist_related_artists(artist_id)

        # Assert
        self.assertEqual(20, len(artists["artists"]))


class TrackSpec(BaseSpec):
    def test_get_track(self):
        # Arrange
        track_id = "spotify:track:2M7FKrVr8intZRw0JZ5BKi"

        # Act
        track = self.sp.track(track_id)

        # Assert
        self.assertEqual(track_id, track["uri"])
        self.assertEqual("Un-Reborn Again", track["name"])

    def test_get_tracks(self):
        # Arrange
        tracks_id = ["spotify:track:2M7FKrVr8intZRw0JZ5BKi", "spotify:track:5abyhgQ3lokXEAWTYMBWJd"]

        # Act
        tracks = self.sp.tracks(tracks_id)

        # Assert
        self.assertEqual(len(tracks_id), len(tracks["tracks"]))
        self.assertEqual("Un-Reborn Again", tracks["tracks"][0]["name"])
        self.assertEqual("Eruption", tracks["tracks"][1]["name"])

    def test_get_track_audio_analysis(self):
        # Arrange
        track_id = "spotify:track:5abyhgQ3lokXEAWTYMBWJd"

        # Act
        audio_analysis = self.sp.track_audio_analysis(track_id)

        # Assert
        self.assertIsNotNone(audio_analysis)

    def test_get_tracks_audio_features(self):
        # Arrange
        tracks_id = ["spotify:track:2M7FKrVr8intZRw0JZ5BKi", "spotify:track:5abyhgQ3lokXEAWTYMBWJd"]

        # Act
        audio_features = self.sp.tracks_audio_feature(tracks_id)

        # Assert
        self.assertEqual(len(tracks_id), len(audio_features["audio_features"]))


class PlayerSpec(BaseSpec):
    def test_set_volume(self):
        # Act
        self.sp.volume(100)

    def test_set_volume_raise_device_not_found_when_device_not_exists(self):
        # Act
        with self.assertRaises(exceptions.DeviceNotFoundError):
            self.sp.volume(100, "foo")

    def test_pause(self):
        # Act
        self.sp.pause_playback()

    def test_play(self):
        # Act
        self.sp.start_playback()

    def test_pause_raise_device_not_found_when_device_not_exists(self):
        # Act
        with self.assertRaises(exceptions.DeviceNotFoundError):
            self.sp.pause_playback("foo")

    def test_play_raise_device_not_found_when_device_not_exists(self):
        # Act
        with self.assertRaises(exceptions.DeviceNotFoundError):
            self.sp.start_playback("foo")

    def test_seek(self):
        # Act
        self.sp.seek_track(1)

    def test_seek_raise_device_not_found_when_device_not_exists(self):
        # Act
        with self.assertRaises(exceptions.DeviceNotFoundError):
            self.sp.seek_track(1, "foo")

    def test_shuffle(self):
        # Act
        self.sp.shuffle(True)

    def test_repeat(self):
        # Act
        self.sp.repeat("context")

    def test_next(self):
        # Act
        self.sp.next_track()

    def test_previous(self):
        # Act
        self.sp.previous_track()

    def test_current_playback(self):
        # Act
        playback = self.sp.current_playback()

        self.assertIsNotNone(playback)

    def test_currently_playing(self):
        # Act
        playing = self.sp.currently_playing()

        self.assertIsNotNone(playing)

    def test_devices(self):
        # Act
        devices = self.sp.devices()

        self.assertIsNotNone(devices)

    def test_transfer_playback(self):
        # Arrange
        devices = self.sp.devices()
        self.assertGreaterEqual(len(devices["devices"]), 1)
        device = devices["devices"][0]

        # Act
        self.sp.transfer_playback(device["id"])

    def test_recently_played(self):
        # Act
        history = self.sp.current_user_recently_played()

        self.assertIsNotNone(history)


class UserSpec(BaseSpec):
    def test_user_profile(self):
        # Act
        profile = self.sp.user("thetufik")

        # Assert
        self.assertIsNotNone(profile)

    def test_me(self):
        # Act
        profile = self.sp.me()

        # Assert
        self.assertIsNotNone(profile)

    def test_me_top_artists(self):
        # Act
        top_artists = self.sp.current_user_top_artists()

        # Assert
        self.assertIsNotNone(top_artists)

    def test_me_top_tracks(self):
        # Act
        top_tracks = self.sp.current_user_top_tracks()

        # Assert
        self.assertIsNotNone(top_tracks)


if __name__ == "__main__":
    unittest.main()
