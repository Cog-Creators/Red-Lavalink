__all__ = [
    "RedLavalinkException",
    "NodeException",
    "PlayerException",
    "NodeNotFound",
    "AbortingNodeConnectionException",
    "NodeNotReady",
    "PlayerNotFound",
]


class RedLavalinkException(Exception):
    """Base exception for all Red-Lavalink exceptions"""


class NodeException(RedLavalinkException):
    """Base exception for all Node related exceptions"""


class PlayerException(RedLavalinkException):
    """Base exception for all Player related exceptions"""


class AbortingNodeConnectionException(NodeException):
    """Error thrown when a connection attempt should be aborted"""


class NodeNotReady(NodeException):
    """Exception raised when a node is not yet ready"""


class NodeNotFound(NodeException):
    """Exception raised when no Node is found"""


class PlayerNotFound(PlayerException):
    """Exception raised when no Player is found"""
