import re
from collections import namedtuple
from typing import Tuple, Union
from urllib.parse import quote, urlparse

from aiohttp import ClientSession
from aiohttp.client_exceptions import ServerDisconnectedError

from . import log
from .enums import *

__all__ = ["Track", "RESTClient", "PlaylistInfo"]


PlaylistInfo = namedtuple("PlaylistInfo", "name selectedTrack")


def parse_timestamps(url, data):

    if data["loadType"] == LoadType.PLAYLIST_LOADED:
        return data["tracks"]

    new_tracks = []
    for track in data["tracks"]:
        start_time = 0
        try:
            query_url = urlparse(url)
            if all([query_url.scheme, query_url.netloc, query_url.path]):
                url_domain = ".".join(query_url.netloc.split(".")[-2:])
                if not query_url.netloc:
                    url_domain = ".".join(query_url.path.split("/")[0].split(".")[-2:])
                if (
                    url_domain in ["youtube.com", "youtu.be"]
                    and "&t=" in track
                    and not all(k in track for k in ["playlist?", "&list="])
                ):
                    match = re.search(r"&t=(\d+)s?", track)
                    if match:
                        start_time = int(match.group(1))
                elif url_domain == "soundcloud.com" and "#t=" in track:
                    if "/sets/" not in track or ("/sets/" in track and "?in=" in track):
                        match = re.search(r"#t=(\d+):(\d+)s?", track)
                        if match:
                            start_time = (int(match.group(1)) * 60) + int(match.group(2))
                elif url_domain == "twitch.tv" and "?t=" in track:
                    match = re.search(r"\?t=(\d+)h(\d+)m(\d+)s", track)
                    if match:
                        start_time = (
                            (int(match.group(1)) * 60 * 60)
                            + (int(match.group(2)) * 60)
                            + int(match.group(3))
                        )
        except Exception:
            pass

        track["info"]["timestamp"] = start_time * 1000
        new_tracks.append(track)
    return new_tracks


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
    start_timestamp: int
        The track start time in milliseconds as provided by the query.
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
        self.start_timestamp = self._info.get("timestamp", 0)

    @property
    def thumbnail(self):
        """Optional[str]: Returns a thumbnail URL for YouTube tracks."""
        if "youtube" in self.uri and "identifier" in self._info:
            return "https://img.youtube.com/vi/{}/mqdefault.jpg".format(self._info["identifier"])

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other, Track):
            return self.number == other.number
        return NotImplemented

    def __ne__(self, other):
        """Overrides the default implementation"""
        x = self.__eq__(other)
        if x is not NotImplemented:
            return not x
        return NotImplemented

    def __hash__(self):
        """Overrides the default implementation"""
        return hash(tuple(sorted(self.__dict__.items())))


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

    _fallback = {
        "loadType": LoadType.LOAD_FAILED,
        "exception": {
            "message": "Lavalink API returned an unsupported response, Please report it.",
            "severity": ExceptionSeverity.SUSPICIOUS,
        },
        "playlistInfo": {},
        "tracks": [],
    }

    def __init__(self, data):
        self._raw = data
        # TODO: Check do we have to support Python 2? from the setup files doesn't look like we do
        for (k, v) in self._fallback.items():
            if k not in data:
                if (
                    k == "exception"
                    and data.get("loadType", LoadType.LOAD_FAILED) != LoadType.LOAD_FAILED
                ):
                    continue
                else:
                    v["message"] = v["message"] + "\n{query}\n{response)".format(
                        query="Query: " + data["encodedquery"] if data.get("encodedquery") else "",
                        response=str(self._raw),
                    )
                data.update({k: v})

        self.load_type = LoadType(data["loadType"])

        is_playlist = self._raw.get("isPlaylist") or self.load_type == LoadType.PLAYLIST_LOADED
        if is_playlist is True:
            self.is_playlist = True
            self.playlist_info = PlaylistInfo(**data["playlistInfo"])
        elif is_playlist is False:
            self.is_playlist = False
            self.playlist_info = None
        else:
            self.is_playlist = None
            self.playlist_info = None
        _tracks = parse_timestamps(self._raw) if self._raw.get("query") else data["tracks"]
        self.tracks = tuple(Track(t) for t in _tracks)

    @property
    def has_error(self):
        return self.load_type == LoadType.LOAD_FAILED

    @property
    def exception_message(self) -> Union[str, None]:
        """
        On Lavalink V3, if there was an exception during a load or get tracks call
        this property will be populated with the error message.
        If there was no error this property will be ``None``.
        """
        if self.has_error:
            exception_data = self._raw.get("exception", {})
            return exception_data.get("message")
        return None

    @property
    def exception_severity(self) -> Union[ExceptionSeverity, None]:
        if self.has_error:
            exception_data = self._raw.get("exception", {})
            severity = exception_data.get("severity")
            if severity is not None:
                return ExceptionSeverity(severity)
        return None


class RESTClient:
    """
    Client class used to access the REST endpoints on a Lavalink node.
    """

    def __init__(self, node):
        self.node = node
        self._session = None
        self._uri = "http://{}:{}/loadtracks?identifier=".format(node.host, node.rest)
        self._headers = {"Authorization": node.password}

        self.state = PlayerState.CONNECTING

        self._warned = False

    def reset_session(self):
        if self._session is None or self._session.closed:
            self._session = ClientSession(loop=self.node.loop)

    def __check_node_ready(self):
        if self.state != PlayerState.READY:
            raise RuntimeError("Cannot execute REST request when node not ready.")

    async def _get(self, url):
        try:
            async with self._session.get(url, headers=self._headers) as resp:
                data = await resp.json(content_type=None)
        except ServerDisconnectedError:
            if self.state == PlayerState.DISCONNECTING:
                return {
                    "loadType": LoadType.LOAD_FAILED,
                    "exception": {
                        "message": "Load tracks interrupted by player disconnect.",
                        "severity": ExceptionSeverity.COMMON,
                    },
                    "tracks": [],
                }
            log.debug(f"Received server disconnected error when player state = {self.state}")
            raise
        return data

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
        _raw_url = str(query)
        url = self._uri + quote(_raw_url)

        data = await self._get(url)

        if isinstance(data, dict):
            data["query"] = _raw_url
            data["encodedquery"] = url
            return LoadResult(data)
        elif isinstance(data, list):
            modified_data = {
                "loadType": LoadType.V2_COMPAT,
                "tracks": data,
                "query": _raw_url,
                "encodedquery": url,
            }
            return LoadResult(modified_data)

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
        if not self._warned:
            log.warn("get_tracks() is now deprecated. Please switch to using load_tracks().")
            self._warned = True
        result = await self.load_tracks(query)
        return result.tracks

    async def search_yt(self, query) -> LoadResult:
        """
        Gets track results from YouTube from Lavalink.

        Parameters
        ----------
        query : str

        Returns
        -------
        list of Track
        """
        return await self.load_tracks("ytsearch:{}".format(query))

    async def search_sc(self, query) -> LoadResult:
        """
        Gets track results from SoundCloud from Lavalink.

        Parameters
        ----------
        query : str

        Returns
        -------
        list of Track
        """
        return await self.load_tracks("scsearch:{}".format(query))

    async def close(self):
        if self._session is not None:
            await self._session.close()
        log.debug("Closed REST session.")
