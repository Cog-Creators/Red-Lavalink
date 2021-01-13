import logging

log = logging.getLogger("red.core.lavalink")
socket_log = logging.getLogger("red.core.lavalink.socket")
socket_log.setLevel(logging.INFO)

from .lavalink import *
from .node import Node, NodeStats, Stats
from .player_manager import *
from .enums import NodeState, PlayerState, TrackEndReason, LavalinkEvents
from .rest_api import Track
from . import utils

__version__ = "0.7.2"
