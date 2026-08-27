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


def _carries(key, layer):
    """Whether `layer` carries `key` at all, empty values included."""
    return key in layer


def effective_value(key, env, project, user, defaults):
    if _carries(key, env):
        return env[key]
    if _carries(key, project):
        return project[key]
    if _carries(key, user):
        return user[key]
    return defaults.get(key)


def describe_source(key, env, project, user, defaults):
    if _carries(key, env):
        return "env"
    if _carries(key, user):
        return "user"
    if _carries(key, project):
        return "project"
    return "default"
