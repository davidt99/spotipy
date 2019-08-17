import contextlib
import socket
import time
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from urllib import parse
from urllib.parse import parse_qs
from urllib.parse import urlparse

import requests

from spotipy import exceptions
from spotipy import auth

PORT = 8080
REDIRECT_ADDRESS = "http://localhost"
REDIRECT_URI = "{}:{}".format(REDIRECT_ADDRESS, PORT)


def prompt_user_for_authorization_code_provider(
    client_id: str,
    client_secret: str,
    redirect_uri: str = None,
    scope: str = None,
    state: str = None,
    show_dialog=False,
    persist_file_path: str = None,
    requests_session: requests.Session = None,
    deploy_local_server=False,
) -> auth.AuthorizationCode:
    """ prompts the user to login if necessary and returns
        the user token suitable for use with the spotipy.Spotify
        constructor

        Parameters:
         - client_id - the client id of your app
         - client_secret - the client secret of your app
         - redirect_uri - The URI to redirect to after the user grants/denies permission
         - scope - the desired scope of the request

         - persist_file_path - path to location to save tokens
         - requests_session - a request.Session object
         - deploy_local_server - if true, will deploy local server to get the authorization code automatically

    """

    redirect_uri = redirect_uri if not deploy_local_server else redirect_uri or REDIRECT_URI
    if not redirect_uri:
        raise ValueError("redirect_uri must be supplied of deploy_local_server is false")

    params = {"client_id": client_id, "response_type": "code", "redirect_uri": redirect_uri}

    if scope:
        params["scope"] = scope
    if state:
        params["state"] = state
    if show_dialog is not None:
        params["show_dialog"] = show_dialog

    auth_url = "{}?{}".format("https://accounts.spotify.com/authorize", parse.urlencode(params))
    print(
        """

        User authentication requires interaction with your
        web browser. You will be prompted to enter your 
        credentials and give authorization.

    """
    )

    code = None
    if deploy_local_server:
        with local_server(redirect_uri) as httpd:
            _open_browser(auth_url)
            code = get_authentication_code(httpd)

    if not code:
        _open_browser(auth_url)
        url = input("Please paste the url you were redirect to:")
        parsed_url = parse.urlparse(url)
        if not parsed_url.query:
            raise ValueError("invalid url")
        code = parse_qs(parsed_url.query)["code"][0]

    payload = {"code": code, "grant_type": "authorization_code", "redirect_uri": redirect_uri}
    now = int(time.time())
    token_info = auth.request_token(payload, client_id, client_secret, requests_session)
    refresh_token = token_info["refresh_token"]
    access_token = token_info["access_token"]
    access_token_expires_at = token_info["expires_in"] + now
    auth_provider = auth.AuthorizationCode(
        client_id,
        client_secret,
        refresh_token,
        access_token,
        access_token_expires_at,
        persist_file_path,
        requests_session,
    )

    if persist_file_path:
        auth_provider.save()
    return auth_provider


def _open_browser(auth_url):
    import webbrowser

    try:
        webbrowser.open(auth_url)
        print("Opened {} in your browser".format(auth_url))
    except Exception:
        print("Please navigate here: {}".format(auth_url))


def assert_port_available(port):
    """
    Assert a given network port is available.
    raise SpotifyException if the port is not available
    :param port: network port to check
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("", port))
    except socket.error:
        raise exceptions.SpotifyError(
            "Port {} is not available. If you are currently running a server, " "please halt it for a min.".format(port)
        )
    finally:
        s.close()


@contextlib.contextmanager
def local_server(redirect_uri: str):
    if redirect_uri != REDIRECT_URI:
        yield
        return
    assert_port_available(PORT)
    httpd = MicroServer((REDIRECT_ADDRESS.split("://")[1], PORT), CustomHandler)
    yield httpd
    httpd.server_close()


def get_authentication_code(httpd):
    """
    Create a temporary http server and get authentication code.
    As soon as a request is received, the server is closed.
    :return: the authentication code
    """
    while not httpd.latest_query_components:
        httpd.handle_request()

    if "error" in httpd.latest_query_components:
        if httpd.latest_query_components["error"][0] == "access_denied":
            raise exceptions.SpotifyError("The user rejected Spotify access")
        else:
            raise exceptions.SpotifyError(
                "Unknown error from Spotify authentication server: {}".format(httpd.latest_query_components["error"][0])
            )
    if "code" in httpd.latest_query_components:
        code = httpd.latest_query_components["code"][0]
    else:
        raise exceptions.SpotifyError(
            "Unknown response from Spotify authentication server: {}".format(httpd.latest_query_components)
        )
    return code


class CustomHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.server.latest_query_components = parse_qs(urlparse(self.path).query)
        self.wfile.write(
            b"""<html>
            <body>
            <p>This tab will be close in 3 seconds</p>
            <script>
            setTimeout(window.close,3000)
            </script>
            </body>
            </html>"""
        )


class MicroServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass):
        self.latest_query_components = None
        super().__init__(server_address, RequestHandlerClass)
