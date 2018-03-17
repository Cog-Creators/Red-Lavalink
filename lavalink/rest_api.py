from typing import Tuple

from aiohttp import ClientSession

from . import log

__all__ = ['Track', 'RESTClient']


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

        self.track_identifier = data.get('track')
        self._info = data.get('info', {})
        self.seekable = self._info.get('isSeekable', False)
        self.author = self._info.get('author')
        self.length = self._info.get('length', 0)
        self.is_stream = self._info.get('isStream', False)
        self.position = self._info.get('position')
        self.title = self._info.get('title')
        self.uri = self._info.get('uri')


class RESTClient:
    """
    Client class used to access the REST endpoints on a Lavalink node.
    """
    def __init__(self, node):
        self._node = node
        self._session = ClientSession(loop=node.loop)
        self._uri = "http://{}:{}/loadtracks?identifier=".format(node.host, node.rest)
        self._headers = {
            'Authorization': node.password
        }

    def _tracks_from_resp(self, resp) -> Tuple[Track, ...]:
        return tuple(Track(d) for d in resp)

    async def get_tracks(self, query):
        """
        Gets tracks from lavalink.

        Parameters
        ----------
        query : str

        Returns
        -------
        list of dict
        """
        url = self._uri + str(query)
        async with self._session.get(url, headers=self._headers) as resp:
            return self._tracks_from_resp(await resp.json(content_type=None))

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
        return await self.get_tracks('ytsearch:{}'.format(query))

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
        return await self.get_tracks('scsearch:{}'.format(query))

    async def close(self):
        await self._session.close()
        log.debug("Closed REST session.")
