import pytest


def pytest_addoption(parser):
    parser.addoption( "--relaxed", action='store_true', help="run tests in relaxed mode")


@pytest.fixture
def relaxed(request):
    return request.config.getoption("--relaxed")
