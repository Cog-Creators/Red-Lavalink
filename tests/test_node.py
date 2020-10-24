from copy import copy

import pytest
import aiohttp


@pytest.mark.asyncio
async def test_node_connected(node):
    assert node._ws.open is True
    headers = copy(node.headers)
    headers.pop(
        "Resume-Key"
    )  # Resume key is added after initial setup and its Unique, so lets ignore it for the tests
    aiohttp.ClientSession.ws_connect.assert_called_once_with(
        url="ws://{}:{}".format(node.host, node.port),
        headers=headers,
        heartbeat=60,
    )
