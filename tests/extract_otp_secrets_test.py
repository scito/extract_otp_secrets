# pytest for extract_otp_secrets.py

# Run tests:
# pytest

# Author: Scito (https://scito.ch)

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations  # workaround for PYTHON <= 3.10

import io
import os
import pathlib
import re
import sys
import time
from enum import Enum
from typing import Any, List, Optional, Tuple

import colorama
import pytest
from pytest_mock import MockerFixture
from utils import (count_files_in_dir, file_exits, read_binary_file_as_stream,
                   read_csv, read_csv_str, read_file_to_str, read_json,
                   read_json_str, replace_escaped_octal_utf8_bytes_with_str)

import extract_otp_secrets

try:
    import cv2  # type: ignore
    from extract_otp_secrets import SUCCESS_COLOR, FAILURE_COLOR, FONT, FONT_SCALE, FONT_COLOR, FONT_THICKNESS, FONT_LINE_STYLE
except ImportError:
    # ignore
    pass

qreader_available: bool = extract_otp_secrets.qreader_available


# Quickfix comment
# @pytest.mark.skipif(sys.platform.startswith("win") or not qreader_available or sys.implementation.name == 'pypy' or sys.version_info >= (3, 10), reason="Quickfix")


def test_extract_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT
    assert captured.err == ''


def test_extract_non_existent_file(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secrets.main(['-n', 'non_existent_file.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '\nERROR: Input file provided is non-existent or not a file.\ninput file: non_existent_file.txt\n'

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


def test_extract_stdin_stdout(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr('sys.stdin', io.StringIO(read_file_to_str('example_export.txt')))

    # Act
    extract_otp_secrets.main(['-'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT
    assert captured.err == ''


def test_extract_stdin_empty(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr('sys.stdin', io.StringIO())

    # Act
    extract_otp_secrets.main(['-n', '-'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == '\nWARN: stdin is empty\n'


def test_extract_stdin_only_comments(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr('sys.stdin', io.StringIO("\n\n# comment 1\n\n\n#comment 2"))

    # Act
    extract_otp_secrets.main(['-n', '-'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == ''


def test_extract_empty_file_no_qreader(capsys: pytest.CaptureFixture[str]) -> None:
    if qreader_available:
        # Act
        with pytest.raises(SystemExit) as e:
            extract_otp_secrets.main(['-n', 'tests/data/empty_file.txt'])

        # Assert
        captured = capsys.readouterr()

        expected_stderr = '\nWARN: tests/data/empty_file.txt is empty\n\nERROR: Unable to open file for reading.\ninput file: tests/data/empty_file.txt\n'

        assert captured.err == expected_stderr
        assert captured.out == ''
        assert e.value.code == 1
        assert e.type == SystemExit
    else:
        # Act
        extract_otp_secrets.main(['tests/data/empty_file.txt'])

        # Assert
        captured = capsys.readouterr()

        assert captured.err == ''
        assert captured.out == ''


def test_extract_only_comments_file_no_qreader(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['-n', 'tests/data/only_comments.txt'])

    # Assert
    captured = capsys.readouterr()

    assert captured.err == ''
    assert captured.out == ''


@pytest.mark.qreader
def test_extract_stdin_img_empty(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr('sys.stdin', io.BytesIO())

    # Act
    extract_otp_secrets.main(['-n', '='])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == '\nWARN: stdin is empty\n'


@pytest.mark.qreader
def test_extract_stdin_img_garbage(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr('sys.stdin', io.BytesIO("garbage".encode('utf-8')))

    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secrets.main(['-n', '='])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == '\nERROR: Unable to open file for reading.\ninput file: =\n'
    assert e.type == SystemExit
    assert e.value.code == 1


def test_extract_csv(capsys: pytest.CaptureFixture[str], tmp_path: pathlib.Path) -> None:
    # Arrange
    output_file = str(tmp_path / 'test_example_output.csv')

    # Act
    extract_otp_secrets.main(['-q', '-c', output_file, 'example_export.txt'])

    # Assert
    expected_csv = read_csv('example_output.csv')
    actual_csv = read_csv(output_file)

    assert actual_csv == expected_csv

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == ''


def test_extract_csv_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['-c', '-', 'example_export.txt'])

    # Assert
    assert not file_exits('test_example_output.csv')

    captured = capsys.readouterr()

    expected_csv = read_csv('example_output.csv')
    actual_csv = read_csv_str(captured.out)

    assert actual_csv == expected_csv
    assert captured.err == ''


def test_extract_csv_stdout_only_comments(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['-c', '-', 'tests/data/only_comments.txt'])

    # Assert
    assert not file_exits('test_example_output.csv')

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == ''


def test_extract_stdin_and_csv_stdout(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr('sys.stdin', io.StringIO(read_file_to_str('example_export.txt')))

    # Act
    extract_otp_secrets.main(['-c', '-', '-'])

    # Assert
    assert not file_exits('test_example_output.csv')

    captured = capsys.readouterr()

    expected_csv = read_csv('example_output.csv')
    actual_csv = read_csv_str(captured.out)

    assert actual_csv == expected_csv
    assert captured.err == ''


def test_keepass_csv(capsys: pytest.CaptureFixture[str], tmp_path: pathlib.Path) -> None:
    '''Two csv files .totp and .htop are generated.'''
    # Arrange
    file_name = str(tmp_path / 'test_example_keepass_output.csv')

    # Act
    extract_otp_secrets.main(['-q', '-k', file_name, 'example_export.txt'])

    # Assert
    expected_totp_csv = read_csv('example_keepass_output.totp.csv')
    expected_hotp_csv = read_csv('example_keepass_output.hotp.csv')
    actual_totp_csv = read_csv(str(tmp_path / 'test_example_keepass_output.totp.csv'))
    actual_hotp_csv = read_csv(str(tmp_path / 'test_example_keepass_output.hotp.csv'))

    assert actual_totp_csv == expected_totp_csv
    assert actual_hotp_csv == expected_hotp_csv
    assert not file_exits(file_name)

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == ''


def test_keepass_empty(capsys: pytest.CaptureFixture[str], tmp_path: pathlib.Path) -> None:
    # Act
    extract_otp_secrets.main(['-k', '-', 'tests/data/only_comments.txt'])

    # Assert

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == ''


def test_keepass_csv_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    '''Two csv files .totp and .htop are generated.'''
    # Act
    extract_otp_secrets.main(['-k', '-', 'tests/data/example_export_only_totp.txt'])

    # Assert
    expected_totp_csv = read_csv('example_keepass_output.totp.csv')
    assert not file_exits('test_example_keepass_output.totp.csv')
    assert not file_exits('test_example_keepass_output.hotp.csv')
    assert not file_exits('test_example_keepass_output.csv')

    captured = capsys.readouterr()
    actual_totp_csv = read_csv_str(captured.out)

    assert actual_totp_csv == expected_totp_csv
    assert captured.err == ''


def test_single_keepass_csv(capsys: pytest.CaptureFixture[str], tmp_path: pathlib.Path) -> None:
    '''Does not add .totp or .hotp pre-suffix'''
    # Act
    extract_otp_secrets.main(['-q', '-k', str(tmp_path / 'test_example_keepass_output.csv'), 'tests/data/example_export_only_totp.txt'])

    # Assert
    expected_totp_csv = read_csv('example_keepass_output.totp.csv')
    actual_totp_csv = read_csv(str(tmp_path / 'test_example_keepass_output.csv'))

    assert actual_totp_csv == expected_totp_csv
    assert not file_exits(tmp_path / 'test_example_keepass_output.totp.csv')
    assert not file_exits(tmp_path / 'test_example_keepass_output.hotp.csv')

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == ''


def test_extract_json(capsys: pytest.CaptureFixture[str], tmp_path: pathlib.Path) -> None:
    # Arrange
    output_file = str(tmp_path / 'test_example_output.json')

    # Act
    extract_otp_secrets.main(['-q', '-j', output_file, 'example_export.txt'])

    # Assert
    expected_json = read_json('example_output.json')
    actual_json = read_json(output_file)

    assert actual_json == expected_json

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == ''


def test_extract_json_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['-j', '-', 'example_export.txt'])

    # Assert
    expected_json = read_json('example_output.json')
    assert not file_exits('test_example_output.json')
    captured = capsys.readouterr()
    actual_json = read_json_str(captured.out)

    assert actual_json == expected_json
    assert captured.err == ''


def test_extract_json_stdout_only_comments(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['-j', '-', 'tests/data/only_comments.txt'])

    # Assert
    assert not file_exits('test_example_output.json')
    captured = capsys.readouterr()

    assert captured.out == '[]'
    assert captured.err == ''


def test_extract_not_encoded_plus(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['tests/data/test_plus_problem_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stdout = '''Name:    SerenityLabs:test1@serenitylabs.co.uk
Secret:  A4RFDYMF4GSLUIBQV4ZP67OJEZ2XUQVM
Issuer:  SerenityLabs
Type:    totp

Name:    SerenityLabs:test2@serenitylabs.co.uk
Secret:  SCDDZ7PW5MOZLE3PQCAZM7L4S35K3UDX
Issuer:  SerenityLabs
Type:    totp

Name:    SerenityLabs:test3@serenitylabs.co.uk
Secret:  TR76272RVYO6EAEY2FX7W7R7KUDEGPJ4
Issuer:  SerenityLabs
Type:    totp

Name:    SerenityLabs:test4@serenitylabs.co.uk
Secret:  N2ILWSXSJUQUB7S6NONPJSC62NPG7EXN
Issuer:  SerenityLabs
Type:    totp

'''

    assert captured.out == expected_stdout
    assert captured.err == ''


def test_extract_printqr(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['-p', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stdout = read_file_to_str('tests/data/printqr_output.txt')

    assert captured.out == expected_stdout
    assert captured.err == ''


def test_extract_saveqr(capsys: pytest.CaptureFixture[str], tmp_path: pathlib.Path) -> None:
    # Act
    extract_otp_secrets.main(['-q', '-s', str(tmp_path), 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == ''

    assert os.path.isfile(tmp_path / '1-piraspberrypi-raspberrypi.png')
    assert os.path.isfile(tmp_path / '2-piraspberrypi.png')
    assert os.path.isfile(tmp_path / '3-piraspberrypi.png')
    assert os.path.isfile(tmp_path / '4-piraspberrypi-raspberrypi.png')
    assert os.path.isfile(tmp_path / '5-hotpdemo.png')
    assert os.path.isfile(tmp_path / '6-encodingäÄéÉdemo.png')
    assert count_files_in_dir(tmp_path) == 6


def test_extract_ignored_duplicates(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['-i', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stdout = '''Name:    pi@raspberrypi
Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY
Issuer:  raspberrypi
Type:    totp

Name:    pi@raspberrypi
Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY
Type:    totp

Name:    hotp demo
Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY
Type:    hotp
Counter: 4

Name:    encoding: ¿äÄéÉ? (demo)
Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY
Type:    totp

'''

    expected_stderr = '''Ignored duplicate otp: pi@raspberrypi

Ignored duplicate otp: pi@raspberrypi / raspberrypi

'''

    assert captured.out == expected_stdout
    assert captured.err == expected_stderr


def test_normalize_bytes() -> None:
    assert replace_escaped_octal_utf8_bytes_with_str(
        'Before\\\\302\\\\277\\\\303\nname: enc: \\302\\277\\303\\244\\303\\204\\303\\251\\303\\211?\nAfter') == 'Before\\\\302\\\\277\\\\303\nname: enc: ¿äÄéÉ?\nAfter'


# Generate verbose output:
# for color in '' '-n'; do for level in '' '-v' '-vv' '-vvv'; do python3.11 src/extract_otp_secrets.py example_export.txt $color $level > tests/data/print_verbose_output$color$level.txt; done; done
# workaround for PYTHON <= 3.10
@pytest.mark.skipif(sys.version_info < (3, 10), reason="fileinput.input encoding exists since PYTHON 3.10")
@pytest.mark.parametrize("verbose_level", ['', '-v', '-vv', '-vvv'])
@pytest.mark.parametrize("color", ['', '-n'])
def test_extract_verbose(verbose_level: str, color: str, capsys: pytest.CaptureFixture[str], relaxed: bool) -> None:
    args = ['example_export.txt']
    if verbose_level:
        args.append(verbose_level)
    if color:
        args.append(color)
    # Act
    extract_otp_secrets.main(args)

    # Assert
    captured = capsys.readouterr()

    expected_stdout = normalize_verbose_text(read_file_to_str(f'tests/data/print_verbose_output{color}{verbose_level}.txt'), relaxed or sys.implementation.name == 'pypy')
    actual_stdout = normalize_verbose_text(captured.out, relaxed or sys.implementation.name == 'pypy')

    assert actual_stdout == expected_stdout
    assert captured.err == ''


def normalize_verbose_text(text: str, relaxed: bool) -> str:
    normalized = re.sub('^.+ version: .+$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    if not qreader_available:
        normalized = normalized \
            .replace('QReader installed: True', 'QReader installed: False') \
            .replace('\nQR reading mode: ZBAR\n\n', '')
    if relaxed:
        print('\nRelaxed mode\n')
        normalized = replace_escaped_octal_utf8_bytes_with_str(normalized)
    return normalized


def test_extract_debug(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['-vvv', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stdout = read_file_to_str('tests/data/print_verbose_output.txt')

    assert len(captured.out) > len(expected_stdout)
    assert "DEBUG: " in captured.out
    assert captured.err == ''


def test_extract_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as e:
        # Act
        extract_otp_secrets.main(['-h'])

    # Assert
    captured = capsys.readouterr()

    assert len(captured.out) > 0
    assert "-h, --help" in captured.out and "-v, --verbose" in captured.out
    assert captured.err == ''
    assert e.type == SystemExit
    assert e.value.code == 0


def test_extract_no_arguments(capsys: pytest.CaptureFixture[str], mocker: MockerFixture) -> None:
    if qreader_available:
        # Arrange
        otps = read_json('example_output.json')
        mocker.patch('extract_otp_secrets.extract_otps_from_camera', return_value=otps)

        # Act
        extract_otp_secrets.main(['-c', '-'])

        # Assert
        captured = capsys.readouterr()

        expected_csv = read_csv('example_output.csv')
        actual_csv = read_csv_str(captured.out)

        assert actual_csv == expected_csv
        assert captured.err == ''
    else:
        # Act
        with pytest.raises(SystemExit) as e:
            extract_otp_secrets.main([])

        # Assert
        captured = capsys.readouterr()

        expected_err_msg = 'error: the following arguments are required: infile'

        assert expected_err_msg in captured.err
        assert captured.out == ''
        assert e.value.code == 2
        assert e.type == SystemExit


MockMode = Enum('MockMode', ['REPEAT_FIRST_ENDLESS', 'LOOP_LIST'])


class MockCam:

    read_counter: int = 0
    read_files: List[str] = []
    mock_mode: MockMode

    def __init__(self, files: List[str] = ['example_export.png'], mock_mode: MockMode = MockMode.REPEAT_FIRST_ENDLESS):
        self.read_files = files
        self.image_mode = mock_mode

    def read(self) -> Tuple[bool, Any]:
        if self.image_mode == MockMode.REPEAT_FIRST_ENDLESS:
            file = self.read_files[0]
        elif self.image_mode == MockMode.LOOP_LIST:
            file = self.read_files[self.read_counter]
            self.read_counter += 1

        if file:
            img = cv2.imread(file)
            return True, img
        else:
            return False, None

    def release(self) -> None:
        # ignore
        pass


@pytest.mark.parametrize("qr_reader,file,success", [
    (None, 'example_export.png', True),
    ('ZBAR', 'example_export.png', True),
    ('QREADER', 'example_export.png', True),
    ('QREADER_DEEP', 'example_export.png', True),
    ('CV2', 'example_export.png', True),
    ('CV2_WECHAT', 'example_export.png', True),
    (None, 'tests/data/qr_but_without_otp.png', False),
    ('ZBAR', 'tests/data/qr_but_without_otp.png', False),
    ('QREADER', 'tests/data/qr_but_without_otp.png', False),
    ('QREADER_DEEP', 'tests/data/qr_but_without_otp.png', False),
    ('CV2', 'tests/data/qr_but_without_otp.png', False),
    ('CV2_WECHAT', 'tests/data/qr_but_without_otp.png', False),
    (None, 'tests/data/lena_std.tif', None),
    ('ZBAR', 'tests/data/lena_std.tif', None),
    ('QREADER', 'tests/data/lena_std.tif', None),
    ('QREADER_DEEP', 'tests/data/lena_std.tif', None),
    ('CV2', 'tests/data/lena_std.tif', None),
    ('CV2_WECHAT', 'tests/data/lena_std.tif', None),
])
def test_extract_otps_from_camera(qr_reader: Optional[str], file: str, success: bool, capsys: pytest.CaptureFixture[str], mocker: MockerFixture) -> None:
    if qreader_available:
        # Arrange
        mockCam = MockCam([file])
        mocker.patch('cv2.VideoCapture', return_value=mockCam)
        mocker.patch('cv2.namedWindow')
        mocked_polylines = mocker.patch('cv2.polylines')
        mocker.patch('cv2.imshow')
        mocker.patch('cv2.getTextSize', return_value=([8, 200], False))
        mocked_putText = mocker.patch('cv2.putText')
        mocker.patch('cv2.getWindowImageRect', return_value=[0, 0, 640, 480])
        mocker.patch('cv2.waitKey', return_value=27)
        mocker.patch('cv2.getWindowProperty', return_value=False)
        mocker.patch('cv2.destroyAllWindows')

        args = []
        if qr_reader:
            args.append('-Q')
            args.append(qr_reader)
        # Act
        extract_otp_secrets.main(args)

        # Assert
        captured = capsys.readouterr()

        if success:
            assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT_PNG
            assert captured.err == ''
            mocked_polylines.assert_called_with(mocker.ANY, mocker.ANY, True, SUCCESS_COLOR, mocker.ANY)
            mocked_putText.assert_called_with(mocker.ANY, "3 otps extracted", mocker.ANY, FONT, FONT_SCALE, FONT_COLOR, FONT_THICKNESS, FONT_LINE_STYLE)
        elif success is None:
            assert captured.out == ''
            assert captured.err == ''
            mocked_polylines.assert_not_called()
            mocked_putText.assert_called_with(mocker.ANY, "0 otps extracted", mocker.ANY, FONT, FONT_SCALE, FONT_COLOR, FONT_THICKNESS, FONT_LINE_STYLE)
        else:
            assert captured.out == ''
            assert captured.err != ''
            mocked_polylines.assert_called_with(mocker.ANY, mocker.ANY, True, FAILURE_COLOR, mocker.ANY)
            mocked_putText.assert_called_with(mocker.ANY, "0 otps extracted", mocker.ANY, FONT, FONT_SCALE, FONT_COLOR, FONT_THICKNESS, FONT_LINE_STYLE)
    else:
        # Act
        with pytest.raises(SystemExit) as e:
            extract_otp_secrets.main([])

        # Assert
        captured = capsys.readouterr()

        expected_err_msg = 'error: the following arguments are required: infile'

        assert expected_err_msg in captured.err
        assert captured.out == ''
        assert e.value.code == 2
        assert e.type == SystemExit


def test_verbose_and_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as e:
        # Act
        extract_otp_secrets.main(['-n', '-v', '-q', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    assert len(captured.err) > 0
    assert 'error: argument -q/--quiet: not allowed with argument -v/--verbose' in captured.err
    assert captured.out == ''
    assert e.value.code == 2
    assert e.type == SystemExit


@pytest.mark.parametrize("parameter,parameter_value,stdout_expected,stderr_expected", [
    ('-c', 'outfile', False, False),
    ('-c', '-', True, False),
    ('-k', 'outfile', False, False),
    ('-k', '-', True, False),
    ('-j', 'outfile', False, False),
    ('-s', 'outfile', False, False),
    ('-j', '-', True, False),
    ('-i', None, False, False),
    ('-p', None, True, False),
    ('-Q', 'CV2', False, False),
    ('-C', '0', False, False),
    ('-n', None, False, False),
])
def test_quiet(parameter: str, parameter_value: Optional[str], stdout_expected: bool, stderr_expected: bool, capsys: pytest.CaptureFixture[str], tmp_path: pathlib.Path) -> None:
    if parameter in ['-Q', '-C'] and not qreader_available:
        return

    # Arrange
    args = ['-q', 'example_export.txt', 'example_export.png', parameter]
    if parameter_value == 'outfile':
        args.append(str(tmp_path / parameter_value))
    elif parameter_value:
        args.append(parameter_value)

    # Act
    extract_otp_secrets.main(args)

    # Assert
    captured = capsys.readouterr()

    assert (captured.out == '' and not stdout_expected) or (len(captured.out) > 0 and stdout_expected)
    assert (captured.err == '' and not stderr_expected) or (len(captured.err) > 0 and stderr_expected)


def test_wrong_data(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as e:
        # Act
        extract_otp_secrets.main(['-n', 'tests/data/test_export_wrong_data.txt'])

    # Assert
    captured = capsys.readouterr()

    first_expected_stderr = '''
ERROR: Cannot decode otpauth-migration migration payload.
data=XXXX
Exception: Error parsing message
'''

    # Alpine Linux prints this exception message
    second_expected_stderr = '''
ERROR: Cannot decode otpauth-migration migration payload.
data=XXXX
Exception: unpack requires a buffer of 4 bytes
'''

    assert captured.err == first_expected_stderr or captured.err == second_expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


def test_wrong_content(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['-n', 'tests/data/test_export_wrong_content.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '''
WARN: input is not a otpauth-migration:// url
source: tests/data/test_export_wrong_content.txt
input: Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua.
Maybe a wrong file was given

ERROR: could not parse query parameter in input url
source: tests/data/test_export_wrong_content.txt
url: Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua.
'''

    assert captured.out == ''
    assert captured.err == expected_stderr


def test_one_wrong_file(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['-n', 'tests/data/test_export_wrong_content.txt', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '''
WARN: input is not a otpauth-migration:// url
source: tests/data/test_export_wrong_content.txt
input: Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua.
Maybe a wrong file was given

ERROR: could not parse query parameter in input url
source: tests/data/test_export_wrong_content.txt
url: Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua.
'''

    assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT
    assert captured.err == expected_stderr


def test_one_wrong_file_colored(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['tests/data/test_export_wrong_content.txt', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = f'''{colorama.Fore.RED}
WARN: input is not a otpauth-migration:// url
source: tests/data/test_export_wrong_content.txt
input: Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua.
Maybe a wrong file was given{colorama.Fore.RESET}
{colorama.Fore.RED}
ERROR: could not parse query parameter in input url
source: tests/data/test_export_wrong_content.txt
url: Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua.{colorama.Fore.RESET}
'''

    assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT
    assert captured.err == expected_stderr


def test_one_wrong_line(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr('sys.stdin',
                        io.StringIO(read_file_to_str('tests/data/test_export_wrong_content.txt') + read_file_to_str('example_export.txt')))

    # Act
    extract_otp_secrets.main(['-n', '-'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '''
WARN: input is not a otpauth-migration:// url
source: -
input: Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua.
Maybe a wrong file was given

ERROR: could not parse query parameter in input url
source: -
url: Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua.
'''

    assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT
    assert captured.err == expected_stderr


def test_wrong_prefix(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['-n', 'tests/data/test_export_wrong_prefix.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '''
WARN: input is not a otpauth-migration:// url
source: tests/data/test_export_wrong_prefix.txt
input: QR-Code:otpauth-migration://offline?data=CjUKEPqlBekzoNEukL7qlsjBCDYSDnBpQHJhc3BiZXJyeXBpGgtyYXNwYmVycnlwaSABKAEwAhABGAEgACjr4JKK%2B%2F%2F%2F%2F%2F8B
Maybe a wrong file was given
'''

    expected_stdout = '''Name:    pi@raspberrypi
Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY
Issuer:  raspberrypi
Type:    totp

'''

    assert captured.out == expected_stdout
    assert captured.err == expected_stderr


def test_add_pre_suffix(capsys: pytest.CaptureFixture[str]) -> None:
    assert extract_otp_secrets.add_pre_suffix("name.csv", "totp") == "name.totp.csv"
    assert extract_otp_secrets.add_pre_suffix("name.csv", "") == "name..csv"
    assert extract_otp_secrets.add_pre_suffix("name", "totp") == "name.totp"


@pytest.mark.qreader
def test_img_qr_reader_from_file_happy_path(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['tests/data/test_googleauth_export.png'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT_PNG
    assert captured.err == ''


@pytest.mark.qreader
def test_img_qr_reader_by_parameter(capsys: pytest.CaptureFixture[str], qr_mode: str) -> None:
    # Act
    start_s = time.process_time()
    extract_otp_secrets.main(['--qr', qr_mode, 'tests/data/test_googleauth_export.png'])
    elapsed_s = time.process_time() - start_s

    # Assert
    captured = capsys.readouterr()

    assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT_PNG
    assert captured.err == ''

    print(f"Elapsed time for {qr_mode}: {elapsed_s:.2f}s")


@pytest.mark.qreader
def test_extract_multiple_files_and_mixed(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main([
        'example_export.txt',
        'tests/data/test_googleauth_export.png',
        'example_export.txt',
        'tests/data/test_googleauth_export.png'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT + EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT_PNG + EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT + EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT_PNG
    assert captured.err == ''


@pytest.mark.qreader
def test_img_qr_reader_from_stdin(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    # sys.stdin.buffer should be monkey patched, but it does not work
    monkeypatch.setattr('sys.stdin', read_binary_file_as_stream('tests/data/test_googleauth_export.png'))

    # Act
    extract_otp_secrets.main(['='])

    # Assert
    captured = capsys.readouterr()

    expected_stdout = '''Name:    Test1:test1@example1.com
Secret:  JBSWY3DPEHPK3PXP
Issuer:  Test1
Type:    totp

Name:    Test2:test2@example2.com
Secret:  JBSWY3DPEHPK3PXQ
Issuer:  Test2
Type:    totp

Name:    Test3:test3@example3.com
Secret:  JBSWY3DPEHPK3PXR
Issuer:  Test3
Type:    totp

'''

    assert captured.out == expected_stdout
    assert captured.err == ''


@pytest.mark.qreader
def test_img_qr_reader_from_stdin_wrong_symbol(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    # sys.stdin.buffer should be monkey patched, but it does not work
    monkeypatch.setattr('sys.stdin', read_binary_file_as_stream('tests/data/test_googleauth_export.png'))

    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secrets.main(['-n', '-'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '\nERROR: Binary input was given in stdin, please use = instead of - as infile argument for images.\n'

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


@pytest.mark.qreader
def test_extract_stdin_stdout_wrong_symbol(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr('sys.stdin', io.StringIO(read_file_to_str('example_export.txt')))

    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secrets.main(['-n', '='])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = "\nERROR: Cannot read binary stdin buffer.\nException: a bytes-like object is required, not 'str'\n"

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


@pytest.mark.qreader
def test_img_qr_reader_no_qr_code_in_image(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secrets.main(['-n', 'tests/data/lena_std.tif'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '\nERROR: Unable to read QR Code from file.\ninput file: tests/data/lena_std.tif\n'

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


@pytest.mark.qreader
def test_img_qr_reader_nonexistent_file(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secrets.main(['-n', 'nonexistent.bmp'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '\nERROR: Input file provided is non-existent or not a file.\ninput file: nonexistent.bmp\n'

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


def test_non_image_file(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['-n', 'tests/data/text_masquerading_as_image.jpeg'])

    # Assert
    captured = capsys.readouterr()
    expected_stderr = '''
WARN: input is not a otpauth-migration:// url
source: tests/data/text_masquerading_as_image.jpeg
input: This is just a text file masquerading as an image file.
Maybe a wrong file was given

ERROR: could not parse query parameter in input url
source: tests/data/text_masquerading_as_image.jpeg
url: This is just a text file masquerading as an image file.
'''

    assert captured.err == expected_stderr
    assert captured.out == ''


EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT = '''Name:    pi@raspberrypi
Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY
Issuer:  raspberrypi
Type:    totp

Name:    pi@raspberrypi
Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY
Type:    totp

Name:    pi@raspberrypi
Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY
Type:    totp

Name:    pi@raspberrypi
Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY
Issuer:  raspberrypi
Type:    totp

Name:    hotp demo
Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY
Type:    hotp
Counter: 4

Name:    encoding: ¿äÄéÉ? (demo)
Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY
Type:    totp

'''

EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT_PNG = '''Name:    Test1:test1@example1.com
Secret:  JBSWY3DPEHPK3PXP
Issuer:  Test1
Type:    totp

Name:    Test2:test2@example2.com
Secret:  JBSWY3DPEHPK3PXQ
Issuer:  Test2
Type:    totp

Name:    Test3:test3@example3.com
Secret:  JBSWY3DPEHPK3PXR
Issuer:  Test3
Type:    totp

'''
