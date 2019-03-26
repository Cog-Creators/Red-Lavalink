from typing import Tuple

from aiohttp import ClientSession
from collections import namedtuple
from enum import Enum

from . import log
from .enums import *

from urllib.parse import quote

__all__ = ["Track", "RESTClient", "LoadType", "PlaylistInfo"]


PlaylistInfo = namedtuple("PlaylistInfo", "name selectedTrack")


class LoadType(Enum):
    """
    The result type of a loadtracks request

    Attributes
    ----------
    TRACK_LOADED
    TRACK_LOADED
    PLAYLIST_LOADED
    SEARCH_RESULT
    NO_MATCHES
    LOAD_FAILED
    """

    TRACK_LOADED = "TRACK_LOADED"
    PLAYLIST_LOADED = "PLAYLIST_LOADED"
    SEARCH_RESULT = "SEARCH_RESULT"
    NO_MATCHES = "NO_MATCHES"
    LOAD_FAILED = "LOAD_FAILED"


class Track:
    """
    Information about a Lavalink track.

    Attributes
    ----------
    requester : discord.User
        The user who requested the track.
    track_identifier : str
        Track identifier used by the Lavalink player to play tracks.
    seekable : bool
        Boolean determining if seeking can be done on this track.
    author : str
        The author of this track.
    length : int
        The length of this track in milliseconds.
    is_stream : bool
        Determines whether Lavalink will stream this track.
    position : int
        Current seeked position to begin playback.
    title : str
        Title of this track.
    uri : str
        The playback url of this track.
    """

    def __init__(self, data):
        self.requester = None

        self.track_identifier = data.get("track")
        self._info = data.get("info", {})
        self.seekable = self._info.get("isSeekable", False)
        self.author = self._info.get("author")
        self.length = self._info.get("length", 0)
        self.is_stream = self._info.get("isStream", False)
        self.position = self._info.get("position")
        self.title = self._info.get("title")
        self.uri = self._info.get("uri")

    @property
    def thumbnail(self):
        """Optional[str]: Returns a thumbnail URL for YouTube tracks."""
        if "youtube" in self.uri and "identifier" in self._info:
            return "https://img.youtube.com/vi/{}/mqdefault.jpg".format(self._info["identifier"])


class LoadResult:
    """
    The result of a load_tracks request.

    Attributes
    ----------
    load_type : LoadType
        The result of the loadtracks request
    playlist_info : Optional[PlaylistInfo]
        The playlist information detected by Lavalink
    tracks : Tuple[Track, ...]
        The tracks that were loaded, if any
    """

    def __init__(self, data):
        self._raw = data
        self.load_type = LoadType(data["loadType"])

        if data.get("playlistInfo"):
            self.playlist_info = PlaylistInfo(**data["playlistInfo"])
        else:
            self.playlist_info = None

        self.tracks = tuple(Track(t) for t in data["tracks"])


class RESTClient:
    """
    Client class used to access the REST endpoints on a Lavalink node.
    """

    def __init__(self, node):
        self.node = node
        self._session = ClientSession(loop=node.loop)
        self._uri = "http://{}:{}/loadtracks?identifier=".format(node.host, node.rest)
        self._headers = {"Authorization": node.password}

        self.state = PlayerState.CONNECTING

    def reset_session(self):
        if self._session.closed:
            self._session = ClientSession(loop=self.node.loop)

    def __check_node_ready(self):
        if self.state != PlayerState.READY:
            raise RuntimeError("Cannot execute REST request when node not ready.")

    async def load_tracks(self, query) -> LoadResult:
        """
        Executes a loadtracks request. Only works on Lavalink V3.

        Parameters
        ----------
        query : str

        Returns
        -------
        LoadResult
        """
        self.__check_node_ready()
        url = self._uri + quote(str(query))

        async with self._session.get(url, headers=self._headers) as resp:
            data = await resp.json(content_type=None)

        assert type(data) is dict, "Lavalink V3 is required for this method"
        return LoadResult(data)

    async def get_tracks(self, query) -> Tuple[Track, ...]:
        """
        Gets tracks from lavalink.

        Parameters
        ----------
        query : str

        Returns
        -------
        Tuple[Track, ...]
        """
        self.__check_node_ready()
        url = self._uri + quote(str(query))

        async with self._session.get(url, headers=self._headers) as resp:
            data = await resp.json(content_type=None)

        tracks = data["tracks"] if type(data) is dict else data
        return tuple(Track(t) for t in tracks)

    async def search_yt(self, query) -> Tuple[Track, ...]:
        """
        Gets track results from YouTube from Lavalink.

        Parameters
        ----------
        query : str

        Returns
        -------
        list of Track
        """
        return await self.get_tracks("ytsearch:{}".format(query))

    async def search_sc(self, query) -> Tuple[Track, ...]:
        """
        Gets track results from SoundCloud from Lavalink.

        Parameters
        ----------
        query : str

        Returns
        -------
        list of Track
        """
        return await self.get_tracks("scsearch:{}".format(query))

    async def close(self):
        await self._session.close()
        log.debug("Closed REST session.")
