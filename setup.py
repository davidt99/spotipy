from setuptools import setup

setup(
    name="spotipy",
    version="3.0.0-beta0",
    description="simple client for the Spotify Web API",
    author="@plamere",
    author_email="paul@echonest.com",
    url="http://spotipy.readthedocs.org/",
    install_requires=["requests>=2.22.0"],
    license="LICENSE.txt",
    packages=["spotipy"],
)
