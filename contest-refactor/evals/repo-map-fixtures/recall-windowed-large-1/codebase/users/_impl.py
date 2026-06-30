"""users internal implementation (cross-package wiring lives here, not in __init__)."""
from auth._impl import AuthApi  # users -> auth

class UsersApi:
    def __init__(self):
        self._auth = AuthApi
