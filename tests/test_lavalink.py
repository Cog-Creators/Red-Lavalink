import pytest

import lavalink
import lavalink.player
import lavalink.node


@pytest.mark.asyncio
async def test_initialize(bot):
    await lavalink.initialize(bot, host="localhost", password="password", port=2333)

    assert len(lavalink.node._nodes) == bot.shard_count

    bot.add_listener.assert_called()
