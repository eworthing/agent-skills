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


def effective_value(key, env, project, user, defaults):
    if key in env:
        return env[key]
    if key in project:
        return project[key]
    if key in user:
        return user[key]
    return defaults.get(key)


def describe_source(key, env, project, user, defaults):
    if env.get(key):
        return "env"
    if project.get(key):
        return "project"
    if user.get(key):
        return "user"
    return "default"
