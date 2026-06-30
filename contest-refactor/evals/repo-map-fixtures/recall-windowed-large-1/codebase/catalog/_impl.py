"""catalog internal implementation (cross-package wiring lives here, not in __init__)."""
from search._impl import SearchApi  # catalog -> search

class CatalogApi:
    def __init__(self):
        self._search = SearchApi
