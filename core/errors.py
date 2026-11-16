# -*- coding: utf-8 -*-
class ApiError(Exception):
    """An error that is safe to show to the user. `code` is translated by the interface."""
    def __init__(self, status, code, message="", **extra):
        super().__init__(message or code)
        self.status, self.code, self.message, self.extra = status, code, message or code, extra

    def payload(self):
        d = {"ok": False, "code": self.code, "error": self.message}
        d.update(self.extra)
        return d
