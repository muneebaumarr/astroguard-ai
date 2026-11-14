"""Independent AstroGuard contracts. Import DTOs, enums and protocols from submodules."""
from . import dto, enums, errors, repositories

API_PREFIX = "/api/v1"
CONTRACT_VERSION = "0.1.0"

__all__ = ["API_PREFIX", "CONTRACT_VERSION", "dto", "enums", "errors", "repositories"]
