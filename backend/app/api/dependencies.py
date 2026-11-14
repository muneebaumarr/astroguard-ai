from collections.abc import Iterator
from fastapi import Request

from astroguard_contracts.repositories import AdapterFactory, UnitOfWork


def get_adapter(request: Request) -> AdapterFactory:
    return request.app.state.adapter


def get_uow(request: Request) -> Iterator[UnitOfWork]:
    with get_adapter(request).create_uow() as uow:
        yield uow
