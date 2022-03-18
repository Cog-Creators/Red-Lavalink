import logging
from red_commons.logging import maybe_update_logger_class, getLogger


maybe_update_logger_class()

log = getLogger("red.core.RLL")
socket_log = getLogger("red.core.RLL.socket")
socket_log.setLevel(logging.INFO)

ws_discord_log = getLogger("red.Audio.WS.discord")
ws_ll_log = getLogger("red.Audio.WS.LLNode")
ws_rll_log = getLogger("red.Audio.WS.RLL")


def set_logging_level(level=logging.INFO):
    log.setLevel(level)
    ws_discord_log.setLevel(level)
    ws_ll_log.setLevel(level)
    ws_rll_log.setLevel(level)
