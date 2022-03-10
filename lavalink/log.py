import logging


def _update_logger_class():

    VERBOSE = logging.DEBUG - 3
    TRACE = logging.DEBUG - 5

    class RedTraceLogger(logging.getLoggerClass()):
        def __init__(self, name, level=logging.NOTSET):
            super().__init__(name, level)

            logging.addLevelName(VERBOSE, "VERBOSE")
            logging.addLevelName(TRACE, "TRACE")

        def verbose(self, msg, *args, **kwargs):
            if self.isEnabledFor(VERBOSE):
                self._log(VERBOSE, msg, args, **kwargs)

        def trace(self, msg, *args, **kwargs):
            if self.isEnabledFor(TRACE):

                self._log(TRACE, msg, args, **kwargs)

    if logging.getLoggerClass().__name__ != "RedTraceLogger":
        logging.setLoggerClass(RedTraceLogger)


_update_logger_class()

log = logging.getLogger("red.core.RLL")
socket_log = logging.getLogger("red.core.RLL.socket")
socket_log.setLevel(logging.INFO)

ws_discord_log = logging.getLogger("red.Audio.WS.discord")
ws_ll_log = logging.getLogger("red.Audio.WS.LLNode")
ws_rll_log = logging.getLogger("red.Audio.WS.RLL")


def set_logging_level(level=logging.INFO):
    log.setLevel(level)
    ws_discord_log.setLevel(level)
    ws_ll_log.setLevel(level)
    ws_rll_log.setLevel(level)
