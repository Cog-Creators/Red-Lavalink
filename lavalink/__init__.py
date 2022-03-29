from .log import set_logging_level, log, socket_log, ws_discord_log, ws_ll_log, ws_rll_log

set_logging_level()
__version__ = "0.10.0"

from . import utils
from .lavalink import (
    initialize,
    connect,
    get_player,
    close,
    register_event_listener,
    unregister_event_listener,
    register_update_listener,
    unregister_update_listener,
    register_stats_listener,
    unregister_stats_listener,
    all_players,
    all_connected_players,
    active_players,
    wait_until_ready,
)
from .node import Node, NodeStats, Stats, get_all_nodes
from .player import Player
from .enums import NodeState, PlayerState, TrackEndReason, LavalinkEvents
from .rest_api import Track, RESTClient
from .errors import (
    RedLavalinkException,
    NodeException,
    PlayerException,
    NodeNotFound,
    AbortingNodeConnection,
    NodeNotReady,
    PlayerNotFound,
)

__all__ = [
    "set_logging_level",
    "log",
    "socket_log",
    "ws_discord_log",
    "ws_ll_log",
    "ws_rll_log",
    "utils",
    "Track",
    "NodeState",
    "PlayerState",
    "TrackEndReason",
    "LavalinkEvents",
    "Node",
    "NodeStats",
    "Stats",
    "Player",
    "initialize",
    "connect",
    "get_player",
    "close",
    "register_event_listener",
    "unregister_event_listener",
    "register_update_listener",
    "unregister_update_listener",
    "register_stats_listener",
    "unregister_stats_listener",
    "all_players",
    "all_connected_players",
    "active_players",
    "get_all_nodes",
    "RedLavalinkException",
    "NodeException",
    "PlayerException",
    "NodeNotFound",
    "AbortingNodeConnection",
    "NodeNotReady",
    "PlayerNotFound",
    "wait_until_ready",
]
