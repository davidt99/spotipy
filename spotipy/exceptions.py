class SpotifyError(Exception):
    pass


class DeviceNotFoundError(SpotifyError):
    pass


class SpotifyRequestError(SpotifyError):
    def __init__(self, status: int, message: str):
        super().__init__("spotify api returned {} status code: {}".format(status, message))
        self.status = status
        self.message = message


class Oauth2Error(SpotifyError):
    pass


class RateLimitReached(SpotifyError):
    def __init__(self, retry_after: int):
        super().__init__("rate limit reached, retry after: {}".format(retry_after))
