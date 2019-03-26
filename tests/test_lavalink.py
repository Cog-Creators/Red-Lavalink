import pytest

import lavalink
import lavalink.player_manager
import lavalink.node


@pytest.mark.asyncio
async def test_initialize(bot):
    await lavalink.initialize(bot, "localhost", "password", 2333, 2333)

    assert lavalink.player_manager.user_id == bot.user.id
    assert lavalink.player_manager.channel_finder_func == bot.get_channel

    assert len(lavalink.node._nodes) == bot.shard_count

    bot.add_listener.assert_called()
