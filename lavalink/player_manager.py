import asyncio

from random import randrange
from typing import Optional

import discord

from . import log
from .enums import *
from .rest_api import Track, RESTClient

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import node

__all__ = [
    "user_id",
    "channel_finder_func",
    "Player",
    "PlayerManager",
]

user_id = None
channel_finder_func = lambda channel_id: None


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

    def __init__(self, node_: "node.Node", channel: discord.VoiceChannel):
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
        self.node = node_

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

    @property
    def ready(self) -> bool:
        """
        Whether the underlying node is ready for requests.
        """
        return self.node.ready.is_set()

    async def wait_until_ready(
        self, timeout: Optional[float] = None, no_raise: bool = False
    ) -> bool:
        """
        Waits for the underlying node to become ready.

        If no_raise is set, returns false when a timeout occurs instead of propogating TimeoutError.
        A timeout of None means to wait indefinitely.
        """
        if self.node.ready.is_set():
            return True

        try:
            return await self.node.wait_until_ready(timeout=timeout)
        except asyncio.TimeoutError:
            if no_raise:
                return False
            else:
                raise

    async def connect(self):
        """
        Connects to the voice channel associated with this Player.
        """
        await self.node.join_voice_channel(self.channel.guild.id, self.channel.id)

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
        if self.state == PlayerState.DISCONNECTING:
            return

        await self.update_state(PlayerState.DISCONNECTING)

        guild_id = self.channel.guild.id
        voice_ws = self.node.get_voice_ws(guild_id)

        if not voice_ws.closed:
            await voice_ws.voice_state(guild_id, None)

        await self.node.destroy_guild(guild_id)
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

    async def update_state(self, state: PlayerState):
        if state == self.state:
            return

        log.debug(f"player for guild {self.channel.guild.id} changing state:"
                  f" {self.state.name} -> {state.name}")

        old_state = self.state
        self.state = state

        if old_state == PlayerState.NODE_BUSY and state == PlayerState.READY:
            self.reset_session()
        elif state == PlayerState.DISCONNECTING:
            log.debug(f"Forcing player disconnect for guild {self.channel.guild.id}"
                      f" due to player manager request.")
            await self.disconnect()

    async def handle_event(self, event: "node.LavalinkEvents", extra):
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
        if event == LavalinkEvents.TRACK_END:
            if extra == TrackEndReason.FINISHED:
                await self.play()
            else:
                self._is_playing = False

    async def handle_player_update(self, state: "node.PlayerState"):
        """
        Handles player updates from lavalink.

        Parameters
        ----------
        state : websocket.PlayerState
        """
        if state.position > self.position:
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
            await self.node.play(self.channel.guild.id, track)

    async def stop(self):
        """
        Stops playback from lavalink.

        .. important::

            This method will clear the queue.
        """
        await self.node.stop(self.channel.guild.id)
        self.queue = []
        self.current = None
        self.position = 0
        self._paused = False

    async def skip(self):
        """
        Skips to the next song.
        """
        await self.play()

    async def pause(self, pause: bool = True):
        """
        Pauses the current song.

        Parameters
        ----------
        pause : bool
            Set to ``False`` to resume.
        """
        self._paused = pause
        await self.node.pause(self.channel.guild.id, pause)

    async def set_volume(self, volume: int):
        """
        Sets the volume of Lavalink.

        Parameters
        ----------
        volume : int
            Between 0 and 150
        """
        self._volume = max(min(volume, 150), 0)
        await self.node.volume(self.channel.guild.id, self.volume)

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
            await self.node.seek(self.channel.guild.id, position)


class PlayerManager:
    def __init__(self, node_: "node.Node"):
        self._player_dict = {}
        self.voice_states = {}

        self.node = node_
        self.node.register_state_handler(self.node_state_handler)

    @property
    def players(self):
        return self._player_dict.values()

    @property
    def guild_ids(self):
        return self._player_dict.keys()

    async def create_player(self, channel: discord.VoiceChannel) -> Player:
        """
        Connects to a discord voice channel.

        This function is safe to repeatedly call as it will return an existing
        player if there is one.

        Parameters
        ----------
        channel

        Returns
        -------
        Player
            The created Player object.
        """
        if self._already_in_guild(channel):
            p = self.get_player(channel.guild.id)
            await p.move_to(channel)
        else:
            p = Player(self.node, channel)
            await p.connect()
            self._player_dict[channel.guild.id] = p
            await self.refresh_player_state(p)
        return p

    def _already_in_guild(self, channel: discord.VoiceChannel) -> bool:
        return channel.guild.id in self._player_dict

    def get_player(self, guild_id: int) -> Player:
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
        if guild_id in self._player_dict:
            return self._player_dict[guild_id]
        raise KeyError("No such player for that guild.")

    def _ensure_player(self, channel_id: int):
        channel = channel_finder_func(channel_id)
        if channel is not None:
            try:
                p = self.get_player(channel.guild.id)
            except KeyError:
                log.debug("Received voice channel connection without a player.")
                p = Player(self.node, channel)
                self._player_dict[channel.guild.id] = p
            return p, channel

    async def _remove_player(self, guild_id: int):
        try:
            p = self.get_player(guild_id)
        except KeyError:
            pass
        else:
            del self._player_dict[guild_id]
            await p.update_state(PlayerState.DISCONNECTING)

    async def node_state_handler(self, next_state: NodeState, old_state: NodeState):
        log.debug(f"Received node state update: {old_state.name} -> {next_state.name}")
        if next_state == NodeState.READY:
            await self.update_player_states(PlayerState.READY)
        elif next_state == NodeState.DISCONNECTING:
            await self.update_player_states(PlayerState.DISCONNECTING)
        elif next_state in (NodeState.CONNECTING, NodeState.RECONNECTING):
            await self.update_player_states(PlayerState.NODE_BUSY)

    async def update_player_states(self, state: PlayerState):
        for p in self.players:
            await p.update_state(state)

    async def refresh_player_state(self, player: Player):
        if self.node.state == NodeState.READY:
            await player.update_state(PlayerState.READY)
        elif self.node.state == NodeState.DISCONNECTING:
            await player.update_state(PlayerState.DISCONNECTING)
        else:
            await player.update_state(PlayerState.NODE_BUSY)

    async def on_socket_response(self, data):
        raw_event = data.get("t")
        try:
            event = DiscordVoiceSocketResponses(raw_event)
        except ValueError:
            return

        log.debug("Received Discord WS voice response: %s", data)

        guild_id = data["d"]["guild_id"]
        if guild_id not in self.voice_states:
            self.voice_states[guild_id] = {}

        if event == DiscordVoiceSocketResponses.VOICE_SERVER_UPDATE:
            # Connected for the first time
            socket_event_data = data["d"]

            self.voice_states[guild_id].update({"guild_id": guild_id, "event": socket_event_data})
        elif event == DiscordVoiceSocketResponses.VOICE_STATE_UPDATE:
            channel_id = data["d"]["channel_id"]
            event_user_id = int(data["d"].get("user_id"))

            if event_user_id != user_id:
                return

            if channel_id is None:
                # We disconnected
                log.debug("Received voice disconnect from discord, removing player.")
                self.voice_states[guild_id] = {}
                await self._remove_player(int(guild_id))

            else:
                # After initial connection, get session ID
                p, channel = self._ensure_player(int(channel_id))
                if channel != p.channel:
                    p.channel = channel

            session_id = data["d"]["session_id"]
            self.voice_states[guild_id]["session_id"] = session_id
        else:
            return

        if len(self.voice_states[guild_id]) == 3:
            await self.node.send_lavalink_voice_update(**self.voice_states[guild_id])

    async def disconnect(self):
        """
        Disconnects all players.
        """
        for p in self.players:
            await p.disconnect()
        log.debug("Disconnected players.")
