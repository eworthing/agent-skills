"""search internal implementation (cross-package wiring lives here, not in __init__)."""
from cache._impl import CacheApi  # search -> cache

class SearchApi:
    def __init__(self):
        self._cache = CacheApi
