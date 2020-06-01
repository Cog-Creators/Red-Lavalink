import asyncio
import contextlib
import json
from collections import namedtuple
from typing import Awaitable, List, Optional, cast

import aiohttp
from discord.backoff import ExponentialBackoff

from . import log, socket_log
from .enums import *
from .player_manager import PlayerManager
from .rest_api import Track

__all__ = ["Stats", "Node", "NodeStats", "get_node", "get_nodes_stats", "join_voice"]

_nodes = []  # type: List[Node]

PlayerState = namedtuple("PlayerState", "position time")
MemoryInfo = namedtuple("MemoryInfo", "reservable used free allocated")
CPUInfo = namedtuple("CPUInfo", "cores systemLoad lavalinkLoad")


class Stats:
    def __init__(self, memory, players, active_players, cpu, uptime):
        self.memory = MemoryInfo(**memory)
        self.players = players
        self.active_players = active_players
        self.cpu_info = CPUInfo(**cpu)
        self.uptime = uptime


# Node stats related class below and how it is called is originally from:
# https://github.com/PythonistaGuild/Wavelink/blob/master/wavelink/stats.py#L41
# https://github.com/PythonistaGuild/Wavelink/blob/master/wavelink/websocket.py#L132
class NodeStats:
    def __init__(self, data: dict):
        self.uptime = data["uptime"]

        self.players = data["players"]
        self.playing_players = data["playingPlayers"]

        memory = data["memory"]
        self.memory_free = memory["free"]
        self.memory_used = memory["used"]
        self.memory_allocated = memory["allocated"]
        self.memory_reservable = memory["reservable"]

        cpu = data["cpu"]
        self.cpu_cores = cpu["cores"]
        self.system_load = cpu["systemLoad"]
        self.lavalink_load = cpu["lavalinkLoad"]

        frame_stats = data.get("frameStats", {})
        self.frames_sent = frame_stats.get("sent", -1)
        self.frames_nulled = frame_stats.get("nulled", -1)
        self.frames_deficit = frame_stats.get("deficit", -1)


class Node:

    _is_shutdown = False  # type: bool

    def __init__(
        self, _loop, event_handler, voice_ws_func, host, password, port, rest, user_id, num_shards
    ):
        """
        Represents a Lavalink node.

        Parameters
        ----------
        _loop : asyncio.BaseEventLoop
            The event loop of the bot.
        event_handler
            Function to dispatch events to.
        voice_ws_func : typing.Callable
            Function that takes one argument, guild ID, and returns a websocket.
        host : str
            Lavalink player host.
        password : str
            Password for the Lavalink player.
        port : int
            Port of the Lavalink player event websocket.
        rest : int
            Port for the Lavalink REST API.
        user_id : int
            User ID of the bot.
        num_shards : int
            Number of shards to which the bot is currently connected.
        ready : asyncio.Event
            Set when the connection is up and running, unset when not.
        """
        self.loop = _loop
        self.event_handler = event_handler
        self.get_voice_ws = voice_ws_func
        self.host = host
        self.port = port
        self.rest = rest
        self.password = password
        self.headers = self._get_connect_headers(self.password, user_id, num_shards)

        self.ready = asyncio.Event()

        self._ws = None
        self._listener_task = None
        self.session = aiohttp.ClientSession()

        self._queue = []

        self.state = NodeState.CONNECTING
        self._state_handlers = []

        self.player_manager = PlayerManager(self)

        self.stats = None

        if self not in _nodes:
            _nodes.append(self)

    async def connect(self, timeout=None):
        """
        Connects to the Lavalink player event websocket.

        Parameters
        ----------
        timeout : int
            Time after which to timeout on attempting to connect to the Lavalink websocket,
            ``None`` is considered never, but the underlying code may stop trying past a
            certain point.

        Raises
        ------
        asyncio.TimeoutError
            If the websocket failed to connect after the given time.
        """
        self._is_shutdown = False

        combo_uri = "ws://{}:{}".format(self.host, self.rest)
        uri = "ws://{}:{}".format(self.host, self.port)

        log.debug(
            "Lavalink WS connecting to %s or %s with headers %s", combo_uri, uri, self.headers
        )

        tasks = tuple({self._multi_try_connect(u) for u in (combo_uri, uri)})
        for task in asyncio.as_completed(tasks, timeout=timeout):
            with contextlib.suppress(Exception):
                if await cast(Awaitable[Optional[aiohttp.ClientWebSocketResponse]], task):
                    break
        else:
            raise asyncio.TimeoutError

        log.debug("Creating Lavalink WS listener.")
        self._listener_task = self.loop.create_task(self.listener())

        for data in self._queue:
            await self.send(data)

        self.ready.set()
        self.update_state(NodeState.READY)

    async def wait_until_ready(self, timeout: Optional[float] = None):
        await asyncio.wait_for(self.ready.wait(), timeout=timeout)

    @staticmethod
    def _get_connect_headers(password, user_id, num_shards):
        return {"Authorization": password, "User-Id": str(user_id), "Num-Shards": str(num_shards)}

    @property
    def lavalink_major_version(self):
        if self.state != NodeState.READY:
            raise RuntimeError("Node not ready!")
        return self._ws.response_headers.get("Lavalink-Major-Version")

    async def _multi_try_connect(self, uri):
        backoff = ExponentialBackoff()
        attempt = 1

        while self._is_shutdown is False and (self._ws is None or self._ws.closed):
            try:
                ws = await self.session.ws_connect(url=uri, headers=self.headers)
            except OSError:
                delay = backoff.delay()
                log.debug("Failed connect attempt %s, retrying in %s", attempt, delay)
                await asyncio.sleep(delay)
                attempt += 1
            else:
                self._ws = ws
                return self._ws

    async def listener(self):
        """
        Listener task for receiving ops from Lavalink.
        """
        while self._is_shutdown is False and not self._ws.closed:
            msg = await self._ws.receive()
            if msg.type != aiohttp.WSMsgType.TEXT:
                if msg.type is aiohttp.WSMsgType.ERROR:
                    log.debug("Ignoring exception in listener task", exc_info=msg.data)
                elif msg.type in (
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.CLOSING,
                    aiohttp.WSMsgType.CLOSE,
                ):
                    log.debug("Listener closing: %s", msg.extra)

                break

            data = json.loads(msg.data)
            try:
                op = LavalinkIncomingOp(data.get("op"))
            except ValueError:
                socket_log.debug("Received unknown op: %s", data)
            else:
                socket_log.debug("Received known op: %s", data)
                self.loop.create_task(self._handle_op(op, data))

        self.ready.clear()
        log.debug("Listener exited: ws %s SHUTDOWN %s.", not self._ws.closed, self._is_shutdown)
        self.loop.create_task(self._reconnect())

    async def _handle_op(self, op: LavalinkIncomingOp, data):
        if op == LavalinkIncomingOp.EVENT:
            try:
                event = LavalinkEvents(data.get("type"))
            except ValueError:
                log.debug("Unknown event type: %s", data)
            else:
                self.event_handler(op, event, data)
        elif op == LavalinkIncomingOp.PLAYER_UPDATE:
            state = PlayerState(**data.get("state"))
            self.event_handler(op, state, data)
        elif op == LavalinkIncomingOp.STATS:
            stats = Stats(
                memory=data.get("memory"),
                players=data.get("players"),
                active_players=data.get("playingPlayers"),
                cpu=data.get("cpu"),
                uptime=data.get("uptime"),
            )
            self.stats = NodeStats(data)
            self.event_handler(op, stats, data)

    async def _reconnect(self):
        self.ready.clear()

        if self._is_shutdown is True:
            log.debug("Shutting down Lavalink WS.")
            return

        if self.state != NodeState.CONNECTING:
            self.update_state(NodeState.RECONNECTING)

        log.debug("Attempting Lavalink WS reconnect.")
        try:
            await self.connect()
        except asyncio.TimeoutError:
            log.debug("Failed to reconnect, please reinitialize lavalink when ready.")
        else:
            log.debug("Reconnect successful.")

    def update_state(self, next_state: NodeState):
        if next_state == self.state:
            return

        log.debug(f"Changing node state: {self.state.name} -> {next_state.name}")
        old_state = self.state
        self.state = next_state
        if self.loop.is_closed():
            log.debug("Event loop closed, not notifying state handlers.")
            return
        for handler in self._state_handlers:
            self.loop.create_task(handler(next_state, old_state))

    def register_state_handler(self, func):
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("Argument must be a coroutine object.")

        if func not in self._state_handlers:
            self._state_handlers.append(func)

    def unregister_state_handler(self, func):
        self._state_handlers.remove(func)

    async def join_voice_channel(self, guild_id, channel_id):
        """
        Alternative way to join a voice channel if node is known.
        """
        voice_ws = self.get_voice_ws(guild_id)
        await voice_ws.voice_state(guild_id, channel_id)

    async def disconnect(self):
        """
        Shuts down and disconnects the websocket.
        """
        self._is_shutdown = True
        self.ready.clear()

        self.update_state(NodeState.DISCONNECTING)

        await self.player_manager.disconnect()

        if self._ws is not None and not self._ws.closed:
            await self._ws.close()

        if self._listener_task is not None and not self.loop.is_closed():
            self._listener_task.cancel()

        await self.session.close()

        self._state_handlers = []

        _nodes.remove(self)
        log.debug("Shutdown Lavalink WS.")

    async def send(self, data):
        if self._ws is None or self._ws.closed:
            self._queue.append(data)
        else:
            log.debug("Sending data to Lavalink: %s", data)
            await self._ws.send_json(data)

    async def send_lavalink_voice_update(self, guild_id, session_id, event):
        await self.send(
            {
                "op": LavalinkOutgoingOp.VOICE_UPDATE.value,
                "guildId": str(guild_id),
                "sessionId": session_id,
                "event": event,
            }
        )

    async def destroy_guild(self, guild_id: int):
        await self.send({"op": LavalinkOutgoingOp.DESTROY.value, "guildId": str(guild_id)})

    # Player commands
    async def stop(self, guild_id: int):
        await self.send({"op": LavalinkOutgoingOp.STOP.value, "guildId": str(guild_id)})
        self.event_handler(
            LavalinkIncomingOp.EVENT, LavalinkEvents.QUEUE_END, {"guildId": str(guild_id)}
        )

    async def play(self, guild_id: int, track: Track):
        await self.send(
            {
                "op": LavalinkOutgoingOp.PLAY.value,
                "guildId": str(guild_id),
                "track": track.track_identifier,
            }
        )

    async def pause(self, guild_id, paused):
        await self.send(
            {"op": LavalinkOutgoingOp.PAUSE.value, "guildId": str(guild_id), "pause": paused}
        )

    async def volume(self, guild_id: int, _volume: int):
        await self.send(
            {"op": LavalinkOutgoingOp.VOLUME.value, "guildId": str(guild_id), "volume": _volume}
        )

    async def seek(self, guild_id: int, position: int):
        await self.send(
            {"op": LavalinkOutgoingOp.SEEK.value, "guildId": str(guild_id), "position": position}
        )


def get_node(guild_id: int, ignore_ready_status: bool = False) -> Node:
    """
    Gets a node based on a guild ID, useful for noding separation. If the
    guild ID does not already have a node association, the least used
    node is returned. Skips over nodes that are not yet ready.

    Parameters
    ----------
    guild_id : int
    ignore_ready_status : bool

    Returns
    -------
    Node
    """
    guild_count = 1e10
    least_used = None

    for node in _nodes:
        guild_ids = node.player_manager.guild_ids

        if ignore_ready_status is False and not node.ready.is_set():
            continue
        elif len(guild_ids) < guild_count:
            guild_count = len(guild_ids)
            least_used = node

        if guild_id in guild_ids:
            return node

    if least_used is None:
        raise IndexError("No nodes found.")

    return least_used


def get_nodes_stats():
    return [node.stats for node in _nodes]


async def join_voice(guild_id: int, channel_id: int):
    """
    Joins a voice channel by ID's.

    Parameters
    ----------
    guild_id : int
    channel_id : int
    """
    node = get_node(guild_id)
    voice_ws = node.get_voice_ws(guild_id)
    await voice_ws.voice_state(guild_id, channel_id)


async def disconnect():
    for node in _nodes.copy():
        await node.disconnect()


async def on_socket_response(data):
    raw_event = data.get("t")
    try:
        event = DiscordVoiceSocketResponses(raw_event)
    except ValueError:
        return

    log.debug("Received Discord WS voice response: %s", data)

    guild_id = data["d"]["guild_id"]

    try:
        node = get_node(guild_id, ignore_ready_status=True)
    except IndexError:
        log.debug(f"Received unhandled socket response for guild: {guild_id}")
    else:
        await node.player_manager.on_socket_response(data)
