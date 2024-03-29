from __future__ import annotations

from collections import namedtuple
from types import SimpleNamespace
from typing import NamedTuple

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from discord.gateway import DiscordWebSocket
from discord.ext.commands import AutoShardedBot

import lavalink.node
from lavalink import NodeNotFound, PlayerNotFound


class ProxyWebSocket:
    def __init__(self, open_=True):
        self.open = open_

        self.EMIT = asyncio.Event()
        self.emit_data = "{}"

        self.recv = MagicMock(wraps=self._recv)
        self.send = MagicMock(wraps=self._send)
        self._response = SimpleNamespace()
        self._response.headers = {}

        self._closed = False

    async def _send(self, data):
        pass

    async def _recv(self):
        await self.EMIT.wait()
        self.EMIT.clear()
        return self.emit_data

    async def receive(self):
        await self.EMIT.wait()
        self.EMIT.clear()
        return self.emit_data

    def emit(self, data: str):
        self.emit_data = data
        self.EMIT.set()

    async def close(self):
        self.open = False
        self._closed = True

    @property
    def closed(self):
        return self._closed


class Guild:
    def __init__(self, id, name):
        self.id = id
        self.name = name


class VoiceChannel:
    def __init__(self, id, name):
        self.id = id
        self.name = name


@pytest.fixture(scope="session")
def user():
    User = namedtuple("User", "id")
    return User(1234567890)


@pytest.fixture(scope="session")
def _guild():
    return Guild(987654321, "Testing")


@pytest.fixture(scope="session")
def _voice_channel():
    return VoiceChannel(9999999999, "Testing VC")


@pytest.fixture(scope="session")
def guild(_guild, _voice_channel):
    _guild.get_channel = lambda channel_id: _voice_channel
    return _guild


@pytest.fixture(scope="session")
def voice_channel(guild, _voice_channel):
    _voice_channel.guild = guild
    return _voice_channel


@pytest.fixture
async def bot(user, guild, voice_channel):
    async def voice_state(guild_id=None, channel_id=None):
        pass

    class Client:
        @property
        def closed(self):
            return False

    voice_websocket = MagicMock(spec=DiscordWebSocket)
    voice_websocket.socket = MagicMock(wraps=Client)
    voice_websocket.voice_state = MagicMock(wraps=voice_state)

    conn = MagicMock()
    conn._get_websocket = lambda guild_id: voice_websocket

    bot_ = MagicMock(spec=AutoShardedBot)
    bot_._connection = conn
    bot_.user = user
    bot_.get_guild = lambda guild_id: guild
    bot_.shard_count = 1

    yield bot_


@pytest.fixture(autouse=True)
def patch_node(monkeypatch):
    async def connect(*args, **kwargs):
        return ProxyWebSocket()

    async def send(self, data):
        self._MOCK_send(data)

    websockets_patch = patch("aiohttp.ClientSession.ws_connect", new=MagicMock(wraps=connect))
    monkeypatch.setattr(lavalink.node.Node, "send", send)
    monkeypatch.setattr(lavalink.node.Node, "_MOCK_send", MagicMock(), raising=False)
    websockets_patch.start()
    yield
    websockets_patch.stop()


@pytest.fixture
async def node(bot):
    node_ = lavalink.node.Node(
        event_handler=MagicMock(),
        host="localhost",
        password="password",
        port=2333,
        user_id=bot.user.id,
        num_shards=bot.shard_count,
        resume_key="Test",
        resume_timeout=60,
        bot=bot,
    )

    # node_.send = MagicMock(wraps=send)

    await node_.connect()

    yield node_

    try:
        await node_.disconnect()
    except (PlayerNotFound, NodeNotFound):
        pass


@pytest.fixture
async def initialize_lavalink(bot):
    await lavalink.initialize(bot, host="localhost", password="password", port=2333)
    yield
    await lavalink.close(bot)
