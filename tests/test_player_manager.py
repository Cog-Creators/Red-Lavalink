import pytest

import lavalink.player_manager
import lavalink.node


@pytest.fixture
def voice_server_update(guild):
    def func(guild_id=guild.id):
        return {
            "t": "VOICE_SERVER_UPDATE",
            "s": 87,
            "op": 0,
            "d": {
                "token": "e5bbc4a783a1af5b",
                "guild_id": str(guild_id),
                "endpoint": "us-west43.discord.gg:80",
            },
        }

    return func


@pytest.fixture
def voice_state_update(bot, voice_channel):
    def func(user_id=bot.user.id, channel_id=voice_channel.id, guild_id=voice_channel.guild.id):
        return {
            "user_id": str(user_id),
            "suppress": False,
            "session_id": "744d1ac65d00e31fb7ab29fc2436be3e",
            "self_video": False,
            "self_mute": False,
            "self_deaf": False,
            "mute": False,
            "guild_id": str(guild_id),
            "deaf": False,
            "channel_id": str(channel_id),
        }

    return func


@pytest.mark.asyncio
async def test_autoconnect(bot, voice_channel, voice_server_update, voice_state_update):
    node = lavalink.node.get_node(voice_channel.guild.id)
    node._players_dict[voice_channel.guild.id] = lavalink.player_manager.Player(
        bot, voice_channel
    )
    player = node.get_player(voice_channel.guild.id)
    assert voice_channel.guild.id in set(node.guild_ids)

    server = voice_server_update()
    state = voice_state_update()
    await player.on_voice_server_update(server)
    await player.on_voice_state_update(state)

    assert len(lavalink.all_players()) == 1
    assert lavalink.get_player(voice_channel.guild.id).channel == voice_channel
