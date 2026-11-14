"""Isolate each test run from temp folders owned by other Windows sessions."""
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


_TEMP_ROOT = pytest.StashKey[TemporaryDirectory]()


def pytest_configure(config: pytest.Config) -> None:
    # Respect an explicitly chosen --basetemp. Otherwise avoid pytest's shared
    # pytest-of-<user> directory, which may belong to another execution identity.
    if config.option.basetemp is None:
        root = TemporaryDirectory(prefix="astroguard-tests-", ignore_cleanup_errors=True)
        config.stash[_TEMP_ROOT] = root
        config.option.basetemp = str(Path(root.name) / "run")


def pytest_unconfigure(config: pytest.Config) -> None:
    root = config.stash.get(_TEMP_ROOT, None)
    if root is not None:
        root.cleanup()
