import unittest
from http import HTTPStatus

import spotipy
from spotipy import auth
from spotipy import exceptions

USER_ID = "thetufik"


class BaseSpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.auth_provider = auth.AuthorizationCode.load(".cache")

    def setUp(self) -> None:
        self.sp = spotipy.Spotify(self.auth_provider)
        self.user_id = USER_ID


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
        self.assertEqual(len(albums_id), len(albums))
        self.assertEqual("Jungle", albums[0]["name"])
        self.assertEqual("Little Dark Age", albums[1]["name"])


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
        self.assertEqual(len(artists_id), len(artists))
        self.assertEqual("Maribou State", artists[0]["name"])
        self.assertEqual("Khruangbin", artists[1]["name"])

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
        top_tracks = self.sp.artist_top_tracks(artist_id, "US")

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
        self.assertEqual(len(tracks_id), len(tracks))
        self.assertEqual("Un-Reborn Again", tracks[0]["name"])
        self.assertEqual("Eruption", tracks[1]["name"])

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
        self.assertEqual(len(tracks_id), len(audio_features))

    def test_get_track_audio_features(self):
        # Arrange
        track_id = "spotify:track:2M7FKrVr8intZRw0JZ5BKi"

        # Act
        audio_features = self.sp.track_audio_feature(track_id)

        # Assert
        self.assertIsNotNone(audio_features)


class PlayerSpec(BaseSpec):
    def test_set_volume(self):
        # Act
        self.sp.volume(100)

        # Assert
        playback = self.sp.current_playback()
        self.assertEqual(playback["device"]["volume_percent"], 100)

    def test_set_volume_raise_device_not_found_when_device_not_exists(self):
        # Act
        with self.assertRaises(exceptions.DeviceNotFoundError):
            self.sp.volume(100, "foo")

    def test_play_and_pause(self):
        # Arrange
        original_is_playing = self.sp.currently_playing()["is_playing"]

        # Act 1
        if original_is_playing:
            self.sp.pause_playback()
        else:
            self.sp.start_playback()

        # Assert 1
        is_playing = self.sp.currently_playing()["is_playing"]
        self.assertNotEqual(original_is_playing, is_playing)

        # Act 2
        if is_playing:
            self.sp.pause_playback()
        else:
            self.sp.start_playback()

        # Assert 1
        is_playing = self.sp.currently_playing()["is_playing"]
        self.assertEqual(original_is_playing, is_playing)

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
        position_ms = 10000
        self.sp.seek_track(position_ms)

        # Assert
        playback = self.sp.current_playback()
        self.assertGreaterEqual(playback["progress_ms"], position_ms)

    def test_seek_raise_device_not_found_when_device_not_exists(self):
        # Act
        with self.assertRaises(exceptions.DeviceNotFoundError):
            self.sp.seek_track(1, "foo")

    def test_shuffle(self):
        # Act
        self.sp.shuffle(True)

        # Assert
        playback = self.sp.current_playback()
        self.assertTrue(playback["shuffle_state"])

    def test_repeat(self):
        # Act
        self.sp.repeat("context")

        # Assert
        playback = self.sp.current_playback()
        self.assertEqual(playback["repeat_state"], "context")

    def test_previous(self):
        # Act
        self.sp.previous_track()

    def test_next(self):
        # Act
        self.sp.next_track()

    def test_current_playback(self):
        # Act
        playback = self.sp.current_playback()

        self.assertIsNotNone(playback)

    def test_devices(self):
        # Act
        devices = self.sp.devices()

        self.assertIsNotNone(devices)

    def test_transfer_playback(self):
        # Arrange
        devices = self.sp.devices()
        if len(devices) == 0:
            self.skipTest("No devices found")
        self.assertGreaterEqual(len(devices), 1)
        device = devices[0]

        # Act
        self.sp.transfer_playback(device["id"])

        # Assert
        playback = self.sp.current_playback()
        self.assertEqual(playback["device"]["id"], device["id"])

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


class PlaylistSpec(BaseSpec):
    def setUp(self) -> None:
        super().setUp()
        self.playlist_id = None

    def tearDown(self) -> None:
        if self.playlist_id:
            self.sp.playlist_unfollow(self.playlist_id)

    def test_create_playlist(self):
        # Arrange
        name = "temp"

        # Act
        playlist = self.sp.user_playlist_create(self.user_id, name)
        self.playlist_id = playlist["id"]

        # Assert
        self.assertEqual(name, playlist["name"])

    def test_get_current_user_playlists(self):
        # Act
        playlists = self.sp.current_user_playlists()

        # Assert
        self.assertGreaterEqual(len(playlists["items"]), 10)

    def test_get_user_playlists(self):
        # Act
        playlists = self.sp.user_playlists("shaytidhar")

        # Assert
        self.assertGreaterEqual(len(playlists["items"]), 10)

    def test_get_playlist(self):
        # Act
        playlist = self.sp.playlist("spotify:playlist:1Ciepag1qhGM5yKYJPBK6z")

        # Assert
        self.assertEqual("beta classics", playlist["name"])

    def test_get_playlist_tacks(self):
        # Act
        tracks = self.sp.playlist_tracks("spotify:playlist:1Ciepag1qhGM5yKYJPBK6z")

        # Assert
        self.assertGreaterEqual(len(tracks["items"]), 30)

    def test_add_tack_to_playlist(self):
        # Act 1
        self.playlist_id = self.sp.user_playlist_create(self.user_id, "temp")["id"]

        snapshot_id = self.sp.playlist_add_tracks(self.playlist_id, ["spotify:track:3fU0407Cls1hLW1ap5w2Lr"], 0)

        # Assert
        self.assertIsNotNone(snapshot_id)

    def test_remove_all_track_occurrences_tack_playlist(self):
        # Act 1
        self.playlist_id = self.sp.user_playlist_create(self.user_id, "temp")["id"]
        track = "spotify:track:33yAEqzKXexYM3WlOYtTfQ"
        self.sp.playlist_add_tracks(self.playlist_id, [track], 0)
        snapshot_id = self.sp.playlist_add_tracks(self.playlist_id, [track], 1)

        # Assert 1
        self.assertIsNotNone(snapshot_id)

        # Act 2
        self.sp.playlist_remove_all_occurrences_of_tracks(self.playlist_id, [track], snapshot_id)

        #
        tracks = self.sp.playlist_tracks(self.playlist_id)
        self.assertEqual(0, tracks["total"])

    def test_remove_one_track_occurrence_from_playlist(self):
        # Act 1
        self.playlist_id = self.sp.user_playlist_create(self.user_id, "temp")["id"]
        track = "spotify:track:33yAEqzKXexYM3WlOYtTfQ"
        snapshot_id = self.sp.playlist_add_tracks(self.playlist_id, [track, track], 0)

        # Assert 1
        self.assertIsNotNone(snapshot_id)

        # Act 2
        self.sp.playlist_remove_specific_occurrences_of_tracks(
            self.playlist_id, [{"uri": track, "positions": [1]}], snapshot_id
        )

        # Assert 2
        tracks = self.sp.playlist_tracks(self.playlist_id)
        self.assertEqual(1, tracks["total"])

    def test_replace_playlist_tracks(self):
        # Act 1
        self.playlist_id = self.sp.user_playlist_create(self.user_id, "temp")["id"]
        track = "spotify:track:33yAEqzKXexYM3WlOYtTfQ"
        new_track = "spotify:track:2JB7PvDV0R3Vwbq0iy1WPe"
        snapshot_id = self.sp.playlist_add_tracks(self.playlist_id, [track, track], 0)

        # Assert 1
        self.assertIsNotNone(snapshot_id)

        # Act 2
        self.sp.playlist_replace_tracks(self.playlist_id, [new_track])

        # Assert 2
        tracks = self.sp.playlist_tracks(self.playlist_id)
        self.assertEqual(1, tracks["total"])
        self.assertEqual(new_track, tracks["items"][0]["track"]["uri"])

    def test_reorder_playlist_tracks(self):
        # Act 1
        self.playlist_id = self.sp.user_playlist_create(self.user_id, "temp")["id"]
        track_1 = "spotify:track:33yAEqzKXexYM3WlOYtTfQ"
        track_2 = "spotify:track:2JB7PvDV0R3Vwbq0iy1WPe"
        snapshot_id = self.sp.playlist_add_tracks(self.playlist_id, [track_1, track_2], 0)

        # Assert 1
        self.assertIsNotNone(snapshot_id)

        # Act 2
        self.sp.playlist_reorder_tracks(self.playlist_id, 1, 0, snapshot_id=snapshot_id)

        # Assert 2
        tracks = self.sp.playlist_tracks(self.playlist_id)
        self.assertEqual(2, tracks["total"])
        self.assertEqual(track_2, tracks["items"][0]["track"]["uri"])
        self.assertEqual(track_1, tracks["items"][1]["track"]["uri"])

    def test_change_playlist_details(self):
        # Arrange
        self.playlist_id = self.sp.user_playlist_create(self.user_id, "temp")["id"]

        self.sp.playlist_change_details(self.playlist_id, "foo", description="bar")

        playlist = self.sp.playlist(self.playlist_id)
        self.assertEqual("foo", playlist["name"])
        self.assertEqual("bar", playlist["description"])

    def test_follow_and_unfollow_playlist(self):
        # Act 1
        self.playlist_id = self.sp.user_playlist_create(self.user_id, "temp")["id"]
        track_1 = "spotify:track:33yAEqzKXexYM3WlOYtTfQ"
        track_2 = "spotify:track:2JB7PvDV0R3Vwbq0iy1WPe"
        snapshot_id = self.sp.playlist_add_tracks(self.playlist_id, [track_1, track_2], 0)

        # Assert 1
        self.assertIsNotNone(snapshot_id)

        # Act 2
        self.sp.playlist_unfollow(self.playlist_id)

        # Assert 2
        is_following = self.sp.is_users_follow_playlist(self.playlist_id, [self.user_id])
        self.assertFalse(is_following)

        # Act 3
        self.sp.follow_playlist(self.playlist_id)

        # Assert 3
        is_following = self.sp.is_users_follow_playlist(self.playlist_id, [self.user_id])
        self.assertTrue(is_following)


class FollowSpec(BaseSpec):
    def test_follow_and_unfollow_artists(self):
        # Arrange
        artist_id = ["spotify:artist:3Fobin2AT6OcrkLNsACzt4"]

        # Act 1
        self.sp.follow_artists(artist_id)

        # Assert 1
        is_following = self.sp.is_current_user_following_artists(artist_id)
        self.assertTrue(is_following)

        # Act 2
        self.sp.unfollow_artists(artist_id)

        # Assert 2
        is_following = self.sp.is_current_user_following_artists(artist_id)
        self.assertFalse(is_following)

    def test_follow_and_unfollow_users(self):
        # Arrange
        user_id = ["spotify:user:shaytidhar"]
        is_original_following = self.sp.is_current_user_following_users(user_id)

        # Act 1
        if is_original_following:
            self.sp.unfollow_users(user_id)
        else:
            self.sp.follow_users(user_id)

        # Assert 1
        is_following = self.sp.is_current_user_following_users(user_id)
        self.assertNotEqual(is_following, is_original_following)

        # Act 2
        if is_original_following:
            self.sp.follow_users(user_id)
        else:
            self.sp.unfollow_users(user_id)

        # Assert 2
        is_following = self.sp.is_current_user_following_users(user_id)
        self.assertEqual(is_original_following, is_following)


class SearchSpec(BaseSpec):
    def test_search_for_tracks(self):
        # Act
        result = self.sp.search2(["roadhouse", "blues"], ["track"])

        # Assert
        self.assertGreater(result["tracks"]["total"], 0)

    def test_search_for_specific_track(self):
        # Arrange
        result = self.sp.search2(["roadhouse", "blues"], ["track"])
        total = result["tracks"]["total"]

        # Act
        result = self.sp.search2(["roadhouse blues"], ["track"])
        self.assertGreater(result["tracks"]["total"], 0)
        self.assertGreater(total, result["tracks"]["total"])

    def test_search_for_specific_track_with_exclusion(self):
        # Arrange
        exclude = ["artist:deep purple"]
        result = self.sp.search2(["roadhouse blues"], ["track"])
        total = result["tracks"]["total"]

        # Act
        result = self.sp.search2(["roadhouse blues"], ["track"], exclude)
        self.assertGreater(total, result["tracks"]["total"])

    @unittest.skip("There seems to be a bug in spotify")
    def test_search_for_artist_with_optional(self):
        # Arrange
        result = self.sp.search2(["the doors"], ["artist"])
        total = result["artists"]["total"]

        # Act
        result = self.sp.search2(["the doors"], ["artist"], optional="abba")
        self.assertGreater(result["tracks"]["total"], total)


if __name__ == "__main__":
    unittest.main()
