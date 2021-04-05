import logging

log = logging.getLogger("red.core.RLL")
socket_log = logging.getLogger("red.core.RLL.socket")
socket_log.setLevel(logging.INFO)

ws_discord_log = logging.getLogger("red.Audio.WS.discord")
ws_ll_log = logging.getLogger("red.Audio.WS.LLServer")
ws_rll_log = logging.getLogger("red.Audio.WS.RLL")
log.setLevel(logging.INFO)
ws_discord_log.setLevel(logging.INFO)
ws_ll_log.setLevel(logging.INFO)
ws_rll_log.setLevel(logging.INFO)

from .lavalink import *
from .node import Node, NodeStats, Stats
from .player_manager import *
from .enums import NodeState, PlayerState, TrackEndReason, LavalinkEvents
from .rest_api import Track
from . import utils

__version__ = "0.8.0"
