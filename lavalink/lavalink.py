import asyncio

from . import node
from . import player_manager
from . import rest_api

from discord.ext.commands import Bot

__all__ = ['initialize', 'close', 'register_event_listener', 'unregister_event_listener',
           'register_update_listener', 'unregister_update_listener',
           'register_stats_listener', 'unregister_stats_listener']


_event_listeners = []
_update_listeners = []
_stats_listeners = []
_loop = None


async def initialize(bot: Bot, host, password, rest_port, ws_port,
                     timeout=30):
    """
    Initializes the websocket connection to the lavalink player.

    .. important::

        This function must only be called AFTER the bot has received its
        "on_ready" event!

    Parameters
    ----------
    bot : Bot
        An instance of a discord.py `Bot` object.
    host : str
        The hostname or IP address of the Lavalink node.
    password : str
        The password of the Lavalink node.
    rest_port : int
        The port of the REST API on the Lavalink node.
    ws_port : int
        The websocket port on the Lavalink Node.
    timeout : int
        Amount of time to allow retries to occur, ``None`` is considered forever.
    """
    global _loop
    _loop = bot.loop

    player_manager.user_id = bot.user.id
    player_manager.channel_finder_func = bot.get_channel
    register_event_listener(player_manager.handle_event)
    register_update_listener(player_manager.handle_update)

    lavalink_node = node.Node(
        _loop, dispatch, bot._connection._get_websocket,
        host, password, port=ws_port,
        user_id=player_manager.user_id, num_shards=bot.shard_count
    )

    await lavalink_node.connect(timeout=timeout)

    rest_api.initialize(loop=_loop, host=host, port=rest_port, password=password)

    bot.add_listener(player_manager.on_socket_response)


def register_event_listener(coro):
    """
    Registers a coroutine to receive lavalink event information.

    Parameters
    ----------
    coro

    Raises
    ------
    TypeError
        If ``coro`` is not a coroutine.
    """
    if not asyncio.iscoroutinefunction(coro):
        raise TypeError("Function is not a coroutine.")

    if coro not in _event_listeners:
        _event_listeners.append(coro)


def unregister_event_listener(coro):
    """
    Unregisters coroutines from being event listeners.

    Parameters
    ----------
    coro
    """
    try:
        _event_listeners.remove(coro)
    except ValueError:
        pass


def register_update_listener(coro):
    """
    Registers a coroutine to receive lavalink player update information.

    Parameters
    ----------
    coro

    Raises
    ------
    TypeError
        If ``coro`` is not a coroutine.
    """
    if not asyncio.iscoroutinefunction(coro):
        raise TypeError("Function is not a coroutine.")

    if coro not in _update_listeners:
        _update_listeners.append(coro)


def unregister_update_listener(coro):
    """
    Unregisters coroutines from being player update listeners.

    Parameters
    ----------
    coro
    """
    try:
        _update_listeners.remove(coro)
    except ValueError:
        pass


def register_stats_listener(coro):
    """
    Registers a coroutine to receive lavalink server stats information.

    Parameters
    ----------
    coro

    Raises
    ------
    TypeError
        If ``coro`` is not a coroutine.
    """
    if not asyncio.iscoroutinefunction(coro):
        raise TypeError("Function is not a coroutine.")

    if coro not in _stats_listeners:
        _stats_listeners.append(coro)


def unregister_stats_listener(coro):
    """
    Unregisters coroutines from being server stats listeners.

    Parameters
    ----------
    coro
    """
    try:
        _stats_listeners.remove(coro)
    except ValueError:
        pass


def dispatch(op, data, raw_data):
    listeners = []
    if op == node.LavalinkIncomingOp.EVENT:
        listeners = _event_listeners
    elif op == node.LavalinkIncomingOp.PLAYER_UPDATE:
        listeners = _update_listeners
    elif op == node.LavalinkIncomingOp.STATS:
        listeners = _stats_listeners

    for coro in listeners:
        _loop.create_task(coro(data, raw_data))


async def close():
    """
    Closes the lavalink connection completely.
    """
    unregister_event_listener(player_manager.handle_event)
    unregister_update_listener(player_manager.handle_update)
    await player_manager.disconnect()
    await node.disconnect()
    await rest_api.close()
