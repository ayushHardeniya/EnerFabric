"""Persistence-layer errors, translated to HTTP responses by the API layer."""


class NotFoundError(Exception):
    """Raised when a repository lookup by id finds nothing."""
