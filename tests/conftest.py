import pytest
from typing import Any


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--relaxed", action='store_true', help="run tests in relaxed mode")


@pytest.fixture
def relaxed(request: pytest.FixtureRequest) -> Any:
    return request.config.getoption("--relaxed")
