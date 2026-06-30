"""notifications internal implementation (cross-package wiring lives here, not in __init__)."""
from users._impl import UsersApi  # notifications -> users
from audit._impl import AuditApi  # notifications -> audit

class NotificationsApi:
    def __init__(self):
        self._users = UsersApi
        self._audit = AuditApi
