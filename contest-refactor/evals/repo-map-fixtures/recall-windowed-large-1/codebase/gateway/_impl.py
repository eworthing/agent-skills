"""gateway internal implementation (cross-package wiring lives here, not in __init__)."""
from api._impl import ApiApi  # gateway -> api
from auth._impl import AuthApi  # gateway -> auth

class GatewayApi:
    def __init__(self):
        self._api = ApiApi
        self._auth = AuthApi
