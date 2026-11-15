"""Public workflow failures, independent of HTTP and persistence adapters."""
from astroguard_contracts.errors import Conflict


class ResourceNotFound(Exception):
    pass


class CheckinConflict(Conflict):
    code = "conflict"


class IdempotencyConflict(CheckinConflict):
    code = "idempotency_conflict"
