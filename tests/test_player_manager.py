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
            "t": "VOICE_STATE_UPDATE",
            "s": 84,
            "op": 0,
            "d": {
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
            },
        }

    return func


@pytest.mark.asyncio
async def test_autoconnect(
    initialize_lavalink, voice_channel, voice_server_update, voice_state_update
):
    node = lavalink.node.get_node(voice_channel.guild.id)
    server = voice_server_update()
    state = voice_state_update()
    await node.player_manager.on_socket_response(server)

    assert voice_channel.guild.id not in set(node.player_manager.guild_ids)

    await node.player_manager.on_socket_response(state)

    send_call = {
        "op": "voiceUpdate",
        "guildId": str(voice_channel.guild.id),
        "sessionId": "744d1ac65d00e31fb7ab29fc2436be3e",
        "event": {
            "token": "e5bbc4a783a1af5b",
            "guild_id": str(voice_channel.guild.id),
            "endpoint": "us-west43.discord.gg:80",
        },
    }

    node._MOCK_send.assert_called_with(send_call)

    assert len(lavalink.all_players()) == 1
    assert lavalink.get_player(voice_channel.guild.id).channel == voice_channel
