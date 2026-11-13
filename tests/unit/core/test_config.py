from pathlib import Path

from gquarium.core.config import ENV_VARS, Settings


def test_defaults_without_environment():
    """
    validate an empty environment yields the built-in defaults
    """
    s = Settings.from_env({})
    assert s == Settings()
    assert (s.app_name, s.width, s.height, s.fps, s.port) == ("g-quarium", 854, 480, 15, 8080)


def test_env_overrides_are_parsed_to_the_right_types():
    """
    validate environment variables are converted (ints, floats, paths, lowercase choices)
    """
    s = Settings.from_env({
        "MUSIC_DIR": "/m", "ENCODER": "SOFTWARE", "WIDTH": "320", "IDLE_GRACE_S": "2.5",
        "SCENE": "Static", "APP_NAME": "radio", "LOG_LEVELS": "web=debug",
    })
    assert s.music_dir == Path("/m") and s.encoder == "software" and s.width == 320
    assert s.idle_grace_s == 2.5 and s.scene == "static"
    assert s.app_name == "radio" and s.log_levels == "web=debug"


def test_version_is_the_short_sha():
    """
    validate the git SHA from APP_VERSION is shortened to 7 characters
    """
    assert Settings.from_env({"APP_VERSION": "a1b2c3d4e5f6"}).version == "a1b2c3d"


def test_version_defaults_to_dev():
    """
    validate builds without a SHA report 'dev'
    """
    assert Settings.from_env({}).version == "dev"
    assert Settings(app_version="").version == "dev"


def test_every_env_var_maps_to_a_real_setting_once():
    """
    validate the env var table has no typos or duplicates
    """
    fields = set(Settings.__dataclass_fields__)
    assert all(v.field in fields for v in ENV_VARS)
    assert len({v.name for v in ENV_VARS}) == len(ENV_VARS)
    assert len({v.field for v in ENV_VARS}) == len(ENV_VARS)
