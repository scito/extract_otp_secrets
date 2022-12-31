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

from __future__ import annotations  # for compatibility with PYTHON < 3.11
import io
import os
import pathlib
import sys

import pytest
from pytest_mock import MockerFixture

import extract_otp_secrets
from utils import (file_exits, quick_and_dirty_workaround_encoding_problem,
                   read_binary_file_as_stream, read_csv, read_csv_str,
                   read_file_to_str, read_json, read_json_str,
                   replace_escaped_octal_utf8_bytes_with_str, count_files_in_dir)

qreader_available: bool = extract_otp_secrets.qreader_available


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
        extract_otp_secrets.main(['non_existent_file.txt'])

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
    extract_otp_secrets.main(['-'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'WARN: stdin is empty\n'


# @pytest.mark.skipif(not qreader_available, reason='Test if cv2 and qreader are not available.')
def test_extract_empty_file_no_qreader(capsys: pytest.CaptureFixture[str]) -> None:
    if qreader_available:
        # Act
        with pytest.raises(SystemExit) as e:
            extract_otp_secrets.main(['tests/data/empty_file.txt'])

        # Assert
        captured = capsys.readouterr()

        expected_stderr = 'WARN: tests/data/empty_file.txt is empty\n\nERROR: Unable to open file for reading.\ninput file: tests/data/empty_file.txt\n'

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


@pytest.mark.qreader
def test_extract_stdin_img_empty(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr('sys.stdin', io.BytesIO())

    # Act
    extract_otp_secrets.main(['='])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'WARN: stdin is empty\n'


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


def test_normalize_bytes() -> None:
    assert replace_escaped_octal_utf8_bytes_with_str(
        'Before\\\\302\\\\277\\\\303\nname: enc: \\302\\277\\303\\244\\303\\204\\303\\251\\303\\211?\nAfter') == 'Before\\\\302\\\\277\\\\303\nname: enc: ¿äÄéÉ?\nAfter'


def test_extract_verbose(capsys: pytest.CaptureFixture[str], relaxed: bool) -> None:
    # Act
    extract_otp_secrets.main(['-v', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stdout = read_file_to_str('tests/data/print_verbose_output.txt')

    if not qreader_available:
        expected_stdout = expected_stdout.replace('QReader installed: True', 'QReader installed: False')
        expected_stdout = expected_stdout.replace('QR reading mode: ZBAR\n\n', '')

    if relaxed or sys.implementation.name == 'pypy':
        print('\nRelaxed mode\n')

        assert replace_escaped_octal_utf8_bytes_with_str(captured.out) == replace_escaped_octal_utf8_bytes_with_str(expected_stdout)
        assert quick_and_dirty_workaround_encoding_problem(captured.out) == quick_and_dirty_workaround_encoding_problem(expected_stdout)
    else:
        assert captured.out == expected_stdout
    assert captured.err == ''


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
    assert "-h, --help" in captured.out and "--verbose, -v" in captured.out
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


def test_verbose_and_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as e:
        # Act
        extract_otp_secrets.main(['-v', '-q', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    assert len(captured.err) > 0
    assert 'error: argument --quiet/-q: not allowed with argument --verbose/-v' in captured.err
    assert captured.out == ''
    assert e.value.code == 2
    assert e.type == SystemExit


def test_wrong_data(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as e:
        # Act
        extract_otp_secrets.main(['tests/data/test_export_wrong_data.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '''
ERROR: Cannot decode otpauth-migration migration payload.
data=XXXX
'''

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


def test_wrong_content(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['tests/data/test_export_wrong_content.txt'])

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
    extract_otp_secrets.main(['tests/data/test_export_wrong_content.txt', 'example_export.txt'])

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


def test_one_wrong_line(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setattr('sys.stdin',
                        io.StringIO(read_file_to_str('tests/data/test_export_wrong_content.txt') + read_file_to_str('example_export.txt')))

    # Act
    extract_otp_secrets.main(['-'])

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
    extract_otp_secrets.main(['tests/data/test_export_wrong_prefix.txt'])

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
    extract_otp_secrets.main(['--qr', qr_mode, 'tests/data/test_googleauth_export.png'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT_PNG
    assert captured.err == ''


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
        extract_otp_secrets.main(['-'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '\nBinary input was given in stdin, please use = instead of - as infile argument for images.\n'

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
        extract_otp_secrets.main(['='])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = "\nERROR: Cannot read binary stdin buffer. Exception: a bytes-like object is required, not 'str'\n"

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


@pytest.mark.qreader
def test_img_qr_reader_no_qr_code_in_image(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secrets.main(['tests/data/lena_std.tif'])

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
        extract_otp_secrets.main(['nonexistent.bmp'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '\nERROR: Input file provided is non-existent or not a file.\ninput file: nonexistent.bmp\n'

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


def test_non_image_file(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    extract_otp_secrets.main(['tests/data/text_masquerading_as_image.jpeg'])

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
