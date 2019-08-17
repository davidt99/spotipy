# Spotipy - a Python client for The Spotify Web API

## Description

Spotipy is a thin client library for the Spotify Web API.
**This fork is not compatible with the original spotipy library, see the difference [section](#difference-between-plamerespotipy)** 

## Installation
If you already have [Python](http://www.python.org/) on your system you can install the library simply by downloading the distribution, unpack it and install in the usual fashion:

```bash
python setup.py install
```

You can also install it using a popular package manager with

```bash
pip install git+https://github.com/davidt99/spotipy
```

or

```bash
easy_install spotipy
```


## Dependencies

- Python 3.5 and above, **python 2.7 is not supported**
- [Requests](https://github.com/psf/requests) - spotipy requires the requests package to be installed


## Development status
The library is still in beta, there are few things to do (feel free to open PR):
* Rewrite the browse and library APIs
* Add unit tests to client
* Add integration tests to the authentication module
* Rewrite the examples directory
* Setup documentation

## Authentication

The library provides 3 ways to authenticate:
1. Using client id and client secret according to [Client Credential](https://developer.spotify.com/documentation/general/guides/authorization-guide/#client-credentials-flow) method. This method is best suite when you don't need any user information or user related actions (like play/pause):

```python
import spotipy.auth
auth_provider = spotipy.auth.ClientCredentials(client_id, client_secret)
```
2. Using refresh token and client id and client secret according to [Authorization Code](https://developer.spotify.com/documentation/general/guides/authorization-guide/#authorization-code-flow). This method is best suite when you need to access user information and perform user related actions (like play/pause)

```python
import spotipy.auth
auth_provider = spotipy.auth.AuthorizationCode(
    client_id, client_secret, refresh_token, persist_file_path="~/.spotify-cache"
)
```

In this example, the required parameters to authenticate again is stored in `"~/.spotify-cache` to allow loading the `AuthorizationCode` from a file:

```python
import spotipy.auth
auth_provider = spotipy.auth.AuthorizationCode.load("~/.spotify-cache")
```

A helper method exists to help getting the refresh token:

```python
import spotipy.util
auth_provider = spotipy.util.prompt_user_for_authorization_code_provider(
    client_id,
    client_secret,
    scope="user-read-playback-state user-modify-playback-state",
    persist_file_path="~/.spotify-cache",
    deploy_local_server=True,
)
```

3. Simple access token, good for testing

```python
import spotipy.auth
auth_provider = spotipy.auth.PlainAccessToken(access_token)
```


## Quick Start
To get started, simply install spotipy, create a Spotify object and call methods:

```python
import spotipy
import spotipy.auth
auth_provider = spotipy.auth.AuthorizationCode.load("~/.spotify-cache")
sp = spotipy.Spotify(auth_provider)

results = sp.search("weezer", "track",)
for track in results["tracks"]["items"]:
    print(track["name"])
```

## Difference Between plamere/spotipy
This repository was forked form [plamere/spotipy](https://github.com/plamere/spotipy) since it was no longer maintained.

There are few key differences:

* Python 2.7 is not supported
* The authenticate module was rewritten, see the Authentication [section](#authentication)
* Use the default values that the spotify API uses like limit and offset

Most of the client methods stayed the same but some changed:

* Some playlist methods no longer get the user since the corresponding API removed them
* Some parameter renaming to reflect spotify API naming, avoid shadowing builtins method or for better readability. Example: country rename to market

## Reporting Issues

If you have suggestions, bugs or other issues specific to this library, file them [here](https://github.com/davidt99/spotipy/issues). Or just send me a pull request.


