import asyncio
from typing import Union

import discord


__all__ = (
    "format_time",
    "is_loop_closed",
)


def format_time(time):
    """Formats the given time into HH:MM:SS"""
    h, r = divmod(time / 1000, 3600)
    m, s = divmod(r, 60)

    return f"{h:02d}:{m:02d}:{s:02d}"


VoiceChannel = Union[discord.VoiceChannel, discord.StageChannel]


def is_loop_closed() -> bool:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # no running event loop
        return True

    return loop.is_closed()
