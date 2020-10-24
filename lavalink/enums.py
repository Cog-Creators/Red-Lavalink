import enum

__all__ = [
    "DiscordVoiceSocketResponses",
    "LavalinkEvents",
    "TrackEndReason",
    "LavalinkIncomingOp",
    "LavalinkOutgoingOp",
    "NodeState",
    "PlayerState",
    "LoadType",
    "ExceptionSeverity",
]


class DiscordVoiceSocketResponses(enum.Enum):
    VOICE_STATE_UPDATE = "VOICE_STATE_UPDATE"
    VOICE_SERVER_UPDATE = "VOICE_SERVER_UPDATE"


class LavalinkEvents(enum.Enum):
    """
    An enumeration of the Lavalink Track Events.
    """

    TRACK_END = "TrackEndEvent"
    """The track playback has ended."""

    TRACK_EXCEPTION = "TrackExceptionEvent"
    """There was an exception during track playback."""

    TRACK_STUCK = "TrackStuckEvent"
    """Track playback got stuck during playback."""

    TRACK_START = "TrackStartEvent"
    """The track playback started."""

    WebSocketClosedEvent = "WebSocketClosedEvent"
    """Websocket has been closed."""

    # Custom events
    QUEUE_END = "QueueEndEvent"
    """This is a custom event generated by this library to denote the
    end of all tracks in the queue.
    """


class TrackEndReason(enum.Enum):
    """
    The reasons why track playback has ended.
    """

    FINISHED = "FINISHED"
    """The track reached the end, or the track itself ended with an
    exception.
    """

    LOAD_FAILED = "LOAD_FAILED"
    """The track failed to start, throwing an exception before
    providing any audio.
    """

    STOPPED = "STOPPED"
    """The track was stopped due to the player being stopped.
    """

    REPLACED = "REPLACED"
    """The track stopped playing because a new track started playing.
    """

    CLEANUP = "CLEANUP"
    """The track was stopped because the cleanup threshold for the
    audio player was reached.
    """


class LavalinkIncomingOp(enum.Enum):
    EVENT = "event"
    PLAYER_UPDATE = "playerUpdate"
    STATS = "stats"


class LavalinkOutgoingOp(enum.Enum):
    VOICE_UPDATE = "voiceUpdate"
    DESTROY = "destroy"
    PLAY = "play"
    STOP = "stop"
    PAUSE = "pause"
    SEEK = "seek"
    VOLUME = "volume"


class NodeState(enum.Enum):
    CONNECTING = 0
    READY = 1
    RECONNECTING = 2
    DISCONNECTING = 3


class PlayerState(enum.Enum):
    CONNECTING = 0
    READY = 1
    NODE_BUSY = 2
    RECONNECTING = 3
    DISCONNECTING = 4


class LoadType(enum.Enum):
    """
    The result type of a loadtracks request

    Attributes
    ----------
    TRACK_LOADED
    TRACK_LOADED
    PLAYLIST_LOADED
    SEARCH_RESULT
    NO_MATCHES
    LOAD_FAILED
    """

    TRACK_LOADED = "TRACK_LOADED"
    PLAYLIST_LOADED = "PLAYLIST_LOADED"
    SEARCH_RESULT = "SEARCH_RESULT"
    NO_MATCHES = "NO_MATCHES"
    LOAD_FAILED = "LOAD_FAILED"
    V2_COMPAT = "V2_COMPAT"
    V2_COMPACT = "V2_COMPACT"


class ExceptionSeverity(enum.Enum):
    COMMON = "COMMON"
    SUSPICIOUS = "SUSPICIOUS"
    FATAL = "FATAL"
