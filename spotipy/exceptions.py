class SpotifyError(Exception):
    pass


class Oauth2Error(SpotifyError):
    pass


class RateLimitReached(SpotifyError):
    def __init__(self, retry_after: int):
        super().__init__("rate limit reached, retry after: {}".format(retry_after))
