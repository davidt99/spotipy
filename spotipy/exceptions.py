class SpotifyError(Exception):
    pass


class DeviceNotFoundError(SpotifyError):
    pass


class SpotifyRequestError(SpotifyError):
    def __init__(self, status_code: int, message: str):
        super().__init__("spotify api returned {} status code. error: {}".format(status_code, message))
        self.status = status_code
        self.message = message


class AuthorizationError(SpotifyRequestError):
    pass


class RateLimitReached(SpotifyError):
    def __init__(self, retry_after: int):
        super().__init__("rate limit reached, retry after: {}".format(retry_after))
