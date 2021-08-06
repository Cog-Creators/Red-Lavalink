from typing import Union

import discord


def format_time(time):
    """Formats the given time into HH:MM:SS"""
    h, r = divmod(time / 1000, 3600)
    m, s = divmod(r, 60)

    return f"{h:02d}:{m:02d}:{s:02d}"


VoiceChannel = Union[discord.VoiceChannel, discord.StageChannel]
