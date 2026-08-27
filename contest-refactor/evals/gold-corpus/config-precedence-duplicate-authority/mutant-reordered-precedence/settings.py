"""Settings resolution across four layers.

A key's value comes from the first layer that carries it: process
environment, then the project file, then the user file, then the built-in
defaults. A layer "carries" a key when the key is present, whatever the
value -- an explicitly empty string is a deliberate override, not an
absence.

`effective_value` answers "what is this key set to". `describe_source`
answers "which layer did that come from", and is what the --explain
command prints.
"""

ORDER = ("env", "project", "user")


def _resolve(key, env, project, user, defaults):
    """The value for `key` and the layer it came from, decided once."""
    for name, layer in (("env", env), ("user", user), ("project", project)):
        if key in layer:
            return layer[key], name
    return defaults.get(key), "default"


def effective_value(key, env, project, user, defaults):
    return _resolve(key, env, project, user, defaults)[0]


def describe_source(key, env, project, user, defaults):
    return _resolve(key, env, project, user, defaults)[1]
