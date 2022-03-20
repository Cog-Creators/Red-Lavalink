from abc import ABC
from typing import Union, TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from .enums import PlayerState
    from .node import Node


def format_time(time):
    """Formats the given time into HH:MM:SS"""
    h, r = divmod(time / 1000, 3600)
    m, s = divmod(r, 60)

    return f"{h:02d}:{m:02d}:{s:02d}"


VoiceChannel = Union[discord.VoiceChannel, discord.StageChannel]


class PlayerMeta(ABC, discord.VoiceProtocol):
    client: discord.Client
    channel: VoiceChannel
    node: "Node"
    state: "PlayerState"
    guild: discord.Guild
