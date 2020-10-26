from copy import copy

import pytest
import aiohttp


@pytest.mark.asyncio
async def test_node_connected(node):
    assert node._ws.open is True
    headers = copy(node.headers)
    aiohttp.ClientSession.ws_connect.assert_called_once_with(
        url="ws://{}:{}".format(node.host, node.port),
        headers=headers,
        heartbeat=60,
    )
