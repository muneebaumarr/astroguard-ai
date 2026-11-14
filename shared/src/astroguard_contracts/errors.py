"""Adapters translate storage exceptions to these errors; services map HTTP errors."""


class RepositoryError(Exception):
    """Base persistence boundary error."""


class Conflict(RepositoryError):
    """A uniqueness or state constraint prevents the operation."""


class RepositoryUnavailable(RepositoryError):
    """Persistence cannot currently service the operation."""


class ConcurrentWrite(Conflict):
    """An optimistic progress/version precondition no longer matches."""
