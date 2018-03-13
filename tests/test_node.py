import pytest
import lavalink.node


@pytest.mark.asyncio
async def test_node_connected(node):
    assert node._ws.open is True

    lavalink.node.websockets.connect.assert_called_once_with(
        "ws://{}:{}".format(node.host, node.port),
        extra_headers=node.headers
    )
