from typing import Any

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--relaxed", action='store_true', help="run tests in relaxed mode")
    parser.addoption("--fast", action="store_true", help="faster execution, do not run all combinations")


@pytest.fixture
def relaxed(request: pytest.FixtureRequest) -> Any:
    return request.config.getoption("--relaxed")


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "qr_mode" in metafunc.fixturenames:
        all_qr_modes = ['ZBAR', 'QREADER', 'QREADER_DEEP', 'CV2', 'CV2_WECHAT']
        number = 2 if metafunc.config.getoption("fast") else len(all_qr_modes)
        qr_modes = [mode for mode in all_qr_modes]
        metafunc.parametrize("qr_mode", qr_modes[0:number])
