from random import randrange

import discord

from . import log
from . import node
from .rest_api import Track, RESTClient

__all__ = ['players', 'user_id', 'channel_finder_func', 'connect',
           'get_player', 'Player']

players = []
user_id = None
channel_finder_func = lambda channel_id: None

_voice_states = {}


class Player(RESTClient):
    """
    The Player class represents the current state of playback.
    It also is used to control playback and queue tracks.

    The existence of this object guarantees that the bot is connected
    to a voice voice channel.

    Attributes
    ----------
    channel: discord.VoiceChannel
        The channel the bot is connected to.
    queue : list of Track
    position : int
        The seeked position in the track of the current playback.
    current : Track
    repeat : bool
    shuffle : bool
    """
    def __init__(self, node_: node.Node, channel: discord.VoiceChannel):
        super().__init__(node_)
        self.channel = channel

        self.queue = []
        self.position = 0
        self.current = None  # type: Track
        self._paused = False
        self.repeat = False
        self.shuffle = False

        self._volume = 100

        self._is_playing = False
        self._metadata = {}
        self._node = node_

    @property
    def is_playing(self) -> bool:
        """
        Current status of playback
        """
        return self._is_playing and not self._paused

    @property
    def paused(self) -> bool:
        """
        Player's paused state.
        """
        return self._paused

    @property
    def volume(self) -> int:
        """
        The current volume.
        """
        return self._volume

    async def connect(self):
        """
        Connects to the voice channel associated with this Player.
        """
        await node.join_voice(self.channel.guild.id, self.channel.id)

    async def move_to(self, channel: discord.VoiceChannel):
        """
        Moves this player to a voice channel.

        Parameters
        ----------
        channel : discord.VoiceChannel
        """
        if channel.guild != self.channel.guild:
            raise TypeError("Cannot move to a different guild.")

        self.channel = channel
        await self.connect()

    async def disconnect(self):
        """
        Disconnects this player from it's voice channel.
        """
        await node.join_voice(self.channel.guild.id, None)
        await self.close()

    def store(self, key, value):
        """
        Stores a metadata value by key.
        """
        self._metadata[key] = value

    def fetch(self, key, default=None):
        """
        Returns a stored metadata value.

        Parameters
        ----------
        key
            Key used to store metadata.
        default
            Optional, used if the key doesn't exist.
        """
        return self._metadata.get(key, default)

    async def _handle_event(self, event: node.LavalinkEvents, extra):
        """
        Handles various Lavalink Events.

        If the event is TRACK END, extra will be TrackEndReason.

        If the event is TRACK EXCEPTION, extra will be the string reason.

        If the event is TRACK STUCK, extra will be the threshold ms.

        Parameters
        ----------
        event : node.LavalinkEvents
        extra
        """
        if event == node.LavalinkEvents.TRACK_END:
            if extra == node.TrackEndReason.FINISHED:
                await self.play()
            else:
                self._is_playing = False

    async def _handle_player_update(self, state: node.PlayerState):
        """
        Handles player updates from lavalink.

        Parameters
        ----------
        state : websocket.PlayerState
        """
        if state.position > self.position:
            self._paused = False
            self._is_playing = True
        self.position = state.position

    # Play commands
    def add(self, requester: discord.User, track: Track):
        """
        Adds a track to the queue.

        Parameters
        ----------
        requester : discord.User
            User who requested the track.
        track : Track
            Result from any of the lavalink track search methods.
        """
        track.requester = requester
        self.queue.append(track)

    async def play(self):
        """
        Starts playback from lavalink.
        """
        if self.repeat and self.current is not None:
            self.queue.append(self.current)

        self.current = None
        self.position = 0
        self._paused = False

        if not self.queue:
            await self.stop()
        else:
            self._is_playing = True
            if self.shuffle:
                track = self.queue.pop(randrange(len(self.queue)))
            else:
                track = self.queue.pop(0)

            self.current = track
            log.debug("Assigned current.")
            await self._node.play(self.channel.guild.id, track)

    async def stop(self):
        """
        Stops playback from lavalink.

        .. important::

            This method will clear the queue.
        """
        await self._node.stop(self.channel.guild.id)
        self.queue = []
        self.current = None
        self.position = 0
        self._paused = False

    async def skip(self):
        """
        Skips to the next song.
        """
        await self.play()

    async def pause(self, pause: bool=True):
        """
        Pauses the current song.

        Parameters
        ----------
        pause : bool
            Set to ``False`` to resume.
        """
        await self._node.pause(self.channel.guild.id, pause)
        self._paused = pause

    async def set_volume(self, volume: int):
        """
        Sets the volume of Lavalink.

        Parameters
        ----------
        volume : int
            Between 0 and 150
        """
        self._volume = max(min(volume, 150), 0)
        await self._node.volume(self.channel.guild.id, self.volume)

    async def seek(self, position: int):
        """
        If the track allows it, seeks to a position.

        Parameters
        ----------
        position : int
            Between 0 and track length.
        """
        if self.current.seekable:
            position = max(min(position, self.current.length), 0)
            await self._node.seek(self.channel.guild.id, position)


async def connect(channel: discord.VoiceChannel) -> Player:
    """
    Connects to a discord voice channel.

    Parameters
    ----------
    channel

    Returns
    -------
    Player
        The created Player object.
    """
    if _already_in_guild(channel):
        p = get_player(channel.guild.id)
        await p.move_to(channel)
    else:
        ws = node.get_node(channel.guild.id)
        p = Player(ws, channel)
        await p.connect()
        players.append(p)
    return p


def _already_in_guild(channel: discord.VoiceChannel) -> bool:
    for p in players:
        if p.channel.guild == channel.guild:
            return True
    return False


def get_player(guild_id: int) -> Player:
    """
    Gets a Player object from a guild ID.

    Parameters
    ----------
    guild_id : int
        Discord guild ID.

    Returns
    -------
    Player

    Raises
    ------
    KeyError
        If that guild does not have a Player, e.g. is not connected to any
        voice channel.
    """
    for p in players:
        if p.channel.guild.id == guild_id:
            return p
    raise KeyError("No such player for that guild.")


def _ensure_player(channel_id: int):
    channel = channel_finder_func(channel_id)
    if channel is not None:
        try:
            get_player(channel.guild.id)
        except KeyError:
            log.debug("Received voice channel connection without a player.")
            node_ = node.get_node(channel.guild.id)
            players.append(Player(node_, channel))


async def _remove_player(guild_id: int):
    try:
        p = get_player(guild_id)
    except KeyError:
        pass
    else:
        players.remove(p)
        await p.close()


async def on_socket_response(data):
    raw_event = data.get('t')
    try:
        event = node.DiscordVoiceSocketResponses(raw_event)
    except ValueError:
        return

    log.debug('Received Discord WS voice response: {}'.format(data))

    guild_id = data['d']['guild_id']
    if guild_id not in _voice_states:
        _voice_states[guild_id] = {}

    if event == node.DiscordVoiceSocketResponses.VOICE_SERVER_UPDATE:
        # Connected for the first time
        socket_event_data = data['d']

        _voice_states[guild_id].update({
            'guild_id': guild_id,
            'event': socket_event_data
        })
    elif event == node.DiscordVoiceSocketResponses.VOICE_STATE_UPDATE:
        channel_id = data['d']['channel_id']
        event_user_id = int(data['d'].get('user_id'))

        if event_user_id != user_id:
            return

        if channel_id is None:
            # We disconnected
            log.debug("Received voice disconnect from discord, removing player.")
            _voice_states[guild_id] = {}
            await _remove_player(int(guild_id))
        else:
            # After initial connection, get session ID
            _ensure_player(int(channel_id))

            session_id = data['d']['session_id']
            _voice_states[guild_id]['session_id'] = session_id

    if len(_voice_states[guild_id]) == 3:
        node_ = node.get_node(int(guild_id))
        await node_.send_lavalink_voice_update(**_voice_states[guild_id])


async def disconnect():
    """
    Disconnects all players.
    """
    for p in players:
        await p.disconnect()
    log.debug("Disconnected players.")
