"""Test fixtures. Points the CRM client at a stub instead of a real service."""

import pytest

from vahn_mcp import catalogue
from vahn_mcp.crm_client import crm
from tests.stub_service import Stub, start


@pytest.fixture(scope="session")
def stub_server():
    base, server = start()
    yield base
    server.shutdown()


@pytest.fixture(autouse=True)
def crm_stub(stub_server, monkeypatch):
    """Repoint the client at the stub and clear state between tests.

    The catalogue cache is process-global, so it has to be invalidated or one
    test's cached copy leaks into the next test's assertions.
    """
    Stub.reset()
    catalogue.invalidate()
    monkeypatch.setattr(crm, "_base", stub_server)
    yield Stub
    catalogue.invalidate()
