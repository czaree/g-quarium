import io
import logging

import pytest

from gquarium.core import log as log_module
from gquarium.core.log import configure_logging, get_logger, parse_log_levels


@pytest.fixture(autouse=True)
def restore_logging():
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)
    for name in list(log_module._module_loggers):
        logging.getLogger(name).setLevel(logging.NOTSET)
    log_module._module_loggers.clear()


def test_prefix_is_swapped_for_app_name():
    """
    validate log lines show APP_NAME instead of the package name
    """
    out = io.StringIO()
    configure_logging("g-quarium", "info", stream=out)
    get_logger("gquarium.media.pipeline").info("starting pipeline")
    assert "g-quarium.media.pipeline: starting pipeline" in out.getvalue()


def test_other_loggers_keep_their_names():
    """
    validate third-party logger names are not rewritten
    """
    out = io.StringIO()
    configure_logging("g-quarium", "info", stream=out)
    logging.getLogger("PIL.Image").warning("hello")
    assert "PIL.Image: hello" in out.getvalue()


def test_global_level_filters():
    """
    validate LOG_LEVEL sets the global level
    """
    out = io.StringIO()
    configure_logging("x", "warning", stream=out)
    get_logger("gquarium.web.server").info("quiet")
    get_logger("gquarium.web.server").warning("loud")
    assert "quiet" not in out.getvalue() and "loud" in out.getvalue()


def test_per_module_override_raises_detail():
    """
    validate LOG_LEVELS can turn on debug for one module only
    """
    out = io.StringIO()
    configure_logging("x", "info", "media.pipeline=debug", stream=out)
    get_logger("gquarium.media.pipeline").debug("detail")
    get_logger("gquarium.web.server").debug("other")
    assert "detail" in out.getvalue() and "other" not in out.getvalue()


def test_configuring_twice_does_not_duplicate_lines():
    """
    validate repeated configuration installs a single handler
    """
    out = io.StringIO()
    configure_logging("x", "info", stream=io.StringIO())
    configure_logging("x", "info", stream=out)
    get_logger("gquarium.core.log").info("once")
    assert out.getvalue().count("once") == 1


def test_parse_log_levels():
    """
    validate the LOG_LEVELS syntax, including blanks and bad input
    """
    assert parse_log_levels("") == {}
    assert parse_log_levels("media.pipeline=debug, web=info") == {
        "media.pipeline": logging.DEBUG, "web": logging.INFO}
    for bad in ("web", "web=loud", "=debug"):
        with pytest.raises(ValueError):
            parse_log_levels(bad)


def test_unknown_global_level_is_rejected():
    """
    validate a bad LOG_LEVEL fails fast at startup
    """
    with pytest.raises(ValueError):
        configure_logging("x", "chatty", stream=io.StringIO())
