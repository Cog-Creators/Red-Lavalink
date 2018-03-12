import asyncio
import pytest
import lavalink.node
from unittest.mock import MagicMock


class ProxyWebSocket:
    def __init__(self, open_=True):
        self.open = open_

        self.EMIT = asyncio.Event()
        self.emit_data = '{}'

        self.recv = MagicMock(wraps=self._recv)
        self.send = MagicMock()

    async def _recv(self):
        await self.EMIT.wait()
        self.EMIT.clear()
        return self.emit_data

    def emit(self, data: str):
        self.emit_data = data
        self.EMIT.set()

    async def close(self):
        self.open = False

@pytest.fixture
def node(*args):
    old_connect = lavalink.node.websockets.connect

    async def connect(*args, **kwargs):
        return ProxyWebSocket()

    lavalink.node.websockets.connect = MagicMock(wraps=connect)
    loop = asyncio.get_event_loop()
    yield lavalink.node.Node(
        _loop=loop,
        event_handler=MagicMock(),
        voice_ws_func=MagicMock(),
        host='localhost',
        password='password',
        port=2333,
        user_id=123456,
        num_shards=1
    )
    lavalink.node.websockets.connect = old_connect


@pytest.mark.asyncio
async def test_node_connected(node):
    await node.connect()

    assert node._ws.open is True

    lavalink.node.websockets.connect.assert_called_once_with(
        "ws://{}:{}".format(node.host, node.port),
        extra_headers=node.headers
    )
