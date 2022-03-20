import asyncio
import datetime
from random import shuffle
from typing import TYPE_CHECKING, Optional

import discord
from discord.backoff import ExponentialBackoff
from discord.voice_client import VoiceProtocol

from . import log, ws_rll_log
from .enums import (
    LavalinkEvents,
    LavalinkIncomingOp,
    LavalinkOutgoingOp,
    PlayerState,
    TrackEndReason,
)
from .rest_api import RESTClient, Track
from .utils import VoiceChannel

if TYPE_CHECKING:
    from . import node

__all__ = ["Player"]


class Player(RESTClient, VoiceProtocol):
    """
    The Player class represents the current state of playback.
    It also is used to control playback and queue tracks.

    The existence of this object guarantees that the bot is connected
    to a voice channel.

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

    def __call__(self, client: discord.Client, channel: VoiceChannel):
        self.client: discord.Client = client
        self.channel: VoiceChannel = channel

        return self

    def __init__(
        self, client: discord.Client = None, channel: VoiceChannel = None, node: "node.Node" = None
    ):
        self.client = client
        self.channel = channel
        self.guild = channel.guild
        self._last_channel_id = channel.id
        self.queue = []
        self.position = 0
        self.current = None  # type: Track
        self._paused = False
        self.repeat = False
        self.shuffle = False  # Shuffle is done client side now This is a breaking change
        self.shuffle_bumped = True
        self._is_autoplaying = False
        self._auto_play_sent = False
        self._volume = 100
        self.state = PlayerState.CREATED
        self._voice_state = {}
        self.connected_at = None
        self._connected = False

        self._is_playing = False
        self._metadata = {}
        if node is None:
            from .node import get_node

            node = get_node()
        self.node = node

        self._con_delay = None
        self._last_resume = None

        super(VoiceProtocol).__init__(self)
        super(RESTClient).__init__()

    def __repr__(self):
        return (
            "<Player: "
            f"state={self.state.name}, connected={self.connected}, "
            f"guild={self.guild.name!r} ({self.guild.id}), "
            f"channel={self.channel.name!r} ({self.channel.id}), "
            f"playing={self.is_playing}, paused={self.paused}, volume={self.volume}, "
            f"queue_size={len(self.queue)}, current={self.current!r}, "
            f"position={self.position}, "
            f"length={self.current.length if self.current else 0}, node={self.node!r}>"
        )

    @property
    def is_auto_playing(self) -> bool:
        """
        Current status of playback
        """
        return self._is_playing and not self._paused and self._is_autoplaying

    @property
    def is_playing(self) -> bool:
        """
        Current status of playback
        """
        return self._is_playing and not self._paused and self._connected

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
        return self.node.ready

    @property
    def connected(self) -> bool:
        """
        Whether the player is ready to be used.
        """
        return self._connected

    async def on_voice_server_update(self, data: dict) -> None:
        self._voice_state.update({"event": data})
        await self._send_lavalink_voice_update(self._voice_state)

    async def on_voice_state_update(self, data: dict) -> None:
        self._voice_state.update({"sessionId": data["session_id"]})
        if (channel_id := data["channel_id"]) is None:
            ws_rll_log.info("Received voice disconnect from discord, removing player.")
            self._voice_state.clear()
            await self.disconnect(force=True)
        else:
            channel = self.guild.get_channel(int(channel_id))
            if channel != self.channel:
                if self.channel:
                    self._last_channel_id = self.channel.id
                self.channel = channel
        await self._send_lavalink_voice_update({**self._voice_state, "event": data})

    async def _send_lavalink_voice_update(self, voice_state: dict):
        if voice_state.keys() != {"sessionId", "event"}:
            return

        if voice_state["event"].keys() == {"token", "guild_id", "endpoint"}:
            await self.node.send(
                {
                    "op": LavalinkOutgoingOp.VOICE_UPDATE.value,
                    "guildId": str(self.guild.id),
                    "sessionId": voice_state["sessionId"],
                    "event": voice_state["event"],
                }
            )

    async def wait_until_ready(
        self, timeout: Optional[float] = None, no_raise: bool = False
    ) -> bool:
        """
        Waits for the underlying node to become ready.

        If no_raise is set, returns false when a timeout occurs instead of propogating TimeoutError.
        A timeout of None means to wait indefinitely.
        """
        if self.node.ready:
            return True

        try:
            return await self.node.wait_until_ready(timeout=timeout)
        except asyncio.TimeoutError:
            if no_raise:
                return False
            else:
                raise

    async def connect(self, timeout: float = 2.0, reconnect: bool = False, deafen: bool = False):
        """
        Connects to the voice channel associated with this Player.
        """
        self._last_resume = datetime.datetime.now(datetime.timezone.utc)
        self.connected_at = datetime.datetime.now(datetime.timezone.utc)
        self._connected = True
        self.node._players_dict[self.guild.id] = self
        await self.node.refresh_player_state(self)
        await self.guild.change_voice_state(
            channel=self.channel, self_mute=False, self_deaf=deafen
        )

    async def move_to(self, channel: discord.VoiceChannel, deafen: bool = False):
        """
        Moves this player to a voice channel.

        Parameters
        ----------
        channel : discord.VoiceChannel
        """
        if channel.guild != self.guild:
            raise TypeError(f"Cannot move {self!r} to a different guild.")
        if self.channel:
            self._last_channel_id = self.channel.id
        self.channel = channel
        await self.connect(deafen=deafen)
        if self.current:
            await self.resume(
                track=self.current, replace=True, start=self.position, pause=self._paused
            )

    async def disconnect(self, force=False):
        """
        Disconnects this player from it's voice channel.
        """
        self._is_autoplaying = False
        self._is_playing = False
        self._auto_play_sent = False
        self._connected = False
        if self.state == PlayerState.DISCONNECTING:
            return

        await self.update_state(PlayerState.DISCONNECTING)
        guild_id = self.guild.id
        if force:
            log.verbose("Forcing player disconnect for %r due to player manager request.", self)
            self.node.event_handler(
                LavalinkIncomingOp.EVENT,
                LavalinkEvents.FORCED_DISCONNECT,
                {
                    "guildId": guild_id,
                    "code": 42069,
                    "reason": "Forced Disconnect - Do not Reconnect",
                    "byRemote": True,
                    "retries": -1,
                },
            )

        if not self.client.shards[self.guild.shard_id].is_closed():
            await self.guild.change_voice_state(channel=None)
        await self.node.destroy_guild(guild_id)
        self.node.remove_player(self)
        self.cleanup()

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

        ws_rll_log.trace("Player %r changing state: %s -> %s", self, self.state.name, state.name)

        self.state = state

        if self._con_delay:
            self._con_delay = None

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
        log.trace("Received player event for player: %r - %r - %r.", self, event, extra)

        if event == LavalinkEvents.TRACK_END:
            if extra == TrackEndReason.FINISHED:
                await self.play()
        elif event == LavalinkEvents.WEBSOCKET_CLOSED:
            code = extra.get("code")
            if code in (4015, 4014, 4009, 4006, 4000, 1006):
                if not self._con_delay:
                    self._con_delay = ExponentialBackoff(base=1)

    async def handle_player_update(self, state: "node.PositionTime"):
        """
        Handles player updates from lavalink.

        Parameters
        ----------
        state : websocket.PlayerState
        """
        if state.position > self.position:
            self._is_playing = True
        log.trace("Updated player position for player: %r - %ds.", self, state.position // 1000)
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

    def maybe_shuffle(self, sticky_songs: int = 1):
        if self.shuffle and self.queue:  # Keeps queue order consistent unless adding new tracks
            self.force_shuffle(sticky_songs)

    def force_shuffle(self, sticky_songs: int = 1):
        if not self.queue:
            return
        sticky = max(0, sticky_songs)  # Songs to  bypass shuffle
        # Keeps queue order consistent unless adding new tracks
        if sticky > 0:
            to_keep = self.queue[:sticky]
            to_shuffle = self.queue[sticky:]
        else:
            to_shuffle = self.queue
            to_keep = []
        if not self.shuffle_bumped:
            to_keep_bumped = [t for t in to_shuffle if t.extras.get("bumped", None)]
            to_shuffle = [t for t in to_shuffle if not t.extras.get("bumped", None)]
            to_keep.extend(to_keep_bumped)
            # Shuffles whole queue
        shuffle(to_shuffle)
        to_keep.extend(to_shuffle)
        # Keep next track in queue consistent while adding new tracks
        self.queue = to_keep

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

            track = self.queue.pop(0)

            self.current = track
            log.verbose("Assigned current track for player: %r.", self)
            await self.node.play(self.guild.id, track, start=track.start_timestamp, replace=True)

    async def resume(
        self, track: Track, replace: bool = True, start: int = 0, pause: bool = False
    ):
        log.verbose("Resuming current track for player: %r.", self)
        self._is_playing = False
        self._paused = True
        await self.node.play(self.guild.id, track, start=start, replace=replace, pause=True)
        await self.set_volume(self.volume)
        await self.pause(True)
        await self.pause(pause, timed=1)

    async def stop(self):
        """
        Stops playback from lavalink.

        .. important::

            This method will clear the queue.
        """
        await self.node.stop(self.guild.id)
        self.queue = []
        self.current = None
        self.position = 0
        self._paused = False
        self._is_autoplaying = False
        self._auto_play_sent = False
        self._is_playing = False

    async def skip(self):
        """
        Skips to the next song.
        """
        await self.play()

    async def pause(self, pause: bool = True, timed: Optional[int] = None):
        """
        Pauses the current song.

        Parameters
        ----------
        pause : bool
            Set to ``False`` to resume.
        timed : Optional[int]
            If an int is given the op will be called after it.
        """
        if timed is not None:
            await asyncio.sleep(timed)

        self._paused = pause
        await self.node.pause(self.guild.id, pause)

    async def set_volume(self, volume: int):
        """
        Sets the volume of Lavalink.

        Parameters
        ----------
        volume : int
            Between 0 and 150
        """
        self._volume = max(min(volume, 150), 0)
        await self.node.volume(self.guild.id, self.volume)

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
            await self.node.seek(self.guild.id, position)
