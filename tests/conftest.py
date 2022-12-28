from typing import Any

import pytest

from extract_otp_secrets import QRMode


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--relaxed", action='store_true', help="run tests in relaxed mode")
    parser.addoption("--fast", action="store_true", help="faster execution, do not run all combinations")


@pytest.fixture
def relaxed(request: pytest.FixtureRequest) -> Any:
    return request.config.getoption("--relaxed")


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "qr_mode" in metafunc.fixturenames:
        number = 2 if metafunc.config.getoption("fast") else len(QRMode)
        qr_modes = [mode.name for mode in QRMode]
        metafunc.parametrize("qr_mode", qr_modes[0:number])
