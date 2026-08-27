import settings

DEFAULTS = {"retries": "3", "mode": "fast"}


def _call(fn, key, env=None, project=None, user=None):
    return fn(key, env or {}, project or {}, user or {}, DEFAULTS)


def test_env_beats_project():
    assert (
        _call(settings.effective_value, "retries", env={"retries": "9"}, project={"retries": "5"})
        == "9"
    )


def test_project_used_when_no_env():
    assert _call(settings.effective_value, "retries", project={"retries": "5"}) == "5"


def test_default_when_nothing_set():
    assert _call(settings.effective_value, "retries") == "3"
    assert _call(settings.describe_source, "retries") == "default"


def test_source_reports_env():
    assert _call(settings.describe_source, "retries", env={"retries": "9"}) == "env"


def test_source_reports_user():
    assert _call(settings.describe_source, "mode", user={"mode": "slow"}) == "user"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
