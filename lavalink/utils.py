import asyncio
import contextlib

from .log import log


def format_time(time):
    """Formats the given time into HH:MM:SS"""
    h, r = divmod(time / 1000, 3600)
    m, s = divmod(r, 60)

    return "%02d:%02d:%02d" % (h, m, s)


def task_callback_exception(task: asyncio.Task) -> None:
    with contextlib.suppress(asyncio.CancelledError, asyncio.InvalidStateError):
        if exc := task.exception():
            log.exception("%s raised an Exception", task.get_name(), exc_info=exc)


def task_callback_debug(task: asyncio.Task) -> None:
    with contextlib.suppress(asyncio.CancelledError, asyncio.InvalidStateError):
        if exc := task.exception():
            log.debug("%s raised an Exception", task.get_name(), exc_info=exc)


def task_callback_verbose(task: asyncio.Task) -> None:
    with contextlib.suppress(asyncio.CancelledError, asyncio.InvalidStateError):
        if exc := task.exception():
            log.verbose("%s raised an Exception", task.get_name(), exc_info=exc)


def task_callback_trace(task: asyncio.Task) -> None:
    with contextlib.suppress(asyncio.CancelledError, asyncio.InvalidStateError):
        if exc := task.exception():
            log.trace("%s raised an Exception", task.get_name(), exc_info=exc)
