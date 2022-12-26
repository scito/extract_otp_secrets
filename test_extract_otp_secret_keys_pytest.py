# pytest for extract_otp_secret_keys.py

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

import io
import os
import re
import sys

import pytest

import extract_otp_secret_keys
from utils import *

qreader_available = extract_otp_secret_keys.check_module_available('cv2')


def test_extract_stdout(capsys):
    # Act
    extract_otp_secret_keys.main(['example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT
    assert captured.err == ''


@pytest.mark.qreader
def test_extract_multiple_files_and_mixed(capsys):
    # Act
    extract_otp_secret_keys.main([
        'example_export.txt',
        'test/test_googleauth_export.png',
        'example_export.txt',
        'test/test_googleauth_export.png'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT + EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT_PNG + EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT + EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT_PNG
    assert captured.err == ''


def test_extract_non_existent_file(capsys):
    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secret_keys.main(['test/non_existent_file.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '\nERROR: Input file provided is non-existent or not a file.\ninput file: test/non_existent_file.txt\n'

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


def test_extract_stdin_stdout(capsys, monkeypatch):
    # Arrange
    monkeypatch.setattr('sys.stdin', io.StringIO(read_file_to_str('example_export.txt')))

    # Act
    extract_otp_secret_keys.main(['-'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT
    assert captured.err == ''


def test_extract_stdin_empty(capsys, monkeypatch):
    # Arrange
    monkeypatch.setattr('sys.stdin', io.StringIO())

    # Act
    extract_otp_secret_keys.main(['-'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'WARN: stdin is empty\n'


# @pytest.mark.skipif(not qreader_available, reason='Test if cv2 and qreader are not available.')
def test_extract_empty_file_no_qreader(capsys):
    if qreader_available:
        # Act
        with pytest.raises(SystemExit) as e:
            extract_otp_secret_keys.main(['test/empty_file.txt'])

        # Assert
        captured = capsys.readouterr()

        expected_stderr = 'WARN: test/empty_file.txt is empty\n\nERROR: Unable to open file for reading.\ninput file: test/empty_file.txt\n'

        assert captured.err == expected_stderr
        assert captured.out == ''
        assert e.value.code == 1
        assert e.type == SystemExit
    else:
        # Act
        extract_otp_secret_keys.main(['test/empty_file.txt'])

        # Assert
        captured = capsys.readouterr()

        assert captured.err == ''
        assert captured.out == ''


@pytest.mark.qreader
def test_extract_stdin_img_empty(capsys, monkeypatch):
    # Arrange
    monkeypatch.setattr('sys.stdin', io.BytesIO())

    # Act
    extract_otp_secret_keys.main(['='])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == 'WARN: stdin is empty\n'


@pytest.mark.qreader
def test_extract_stdin_stdout_wrong_symbol(capsys, monkeypatch):
    # Arrange
    monkeypatch.setattr('sys.stdin', io.StringIO(read_file_to_str('example_export.txt')))

    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secret_keys.main(['='])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = "\nERROR: Cannot read binary stdin buffer. Exception: a bytes-like object is required, not 'str'\n"

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


def test_extract_csv(capsys):
    # Arrange
    cleanup()

    # Act
    extract_otp_secret_keys.main(['-q', '-c', 'test_example_output.csv', 'example_export.txt'])

    # Assert
    expected_csv = read_csv('example_output.csv')
    actual_csv = read_csv('test_example_output.csv')

    assert actual_csv == expected_csv

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == ''

    # Clean up
    cleanup()


def test_extract_csv_stdout(capsys):
    # Arrange
    cleanup()

    # Act
    extract_otp_secret_keys.main(['-c', '-', 'example_export.txt'])

    # Assert
    assert not file_exits('test_example_output.csv')

    captured = capsys.readouterr()

    expected_csv = read_csv('example_output.csv')
    actual_csv = read_csv_str(captured.out)

    assert actual_csv == expected_csv
    assert captured.err == ''

    # Clean up
    cleanup()


def test_extract_stdin_and_csv_stdout(capsys, monkeypatch):
    # Arrange
    cleanup()
    monkeypatch.setattr('sys.stdin', io.StringIO(read_file_to_str('example_export.txt')))

    # Act
    extract_otp_secret_keys.main(['-c', '-', '-'])

    # Assert
    assert not file_exits('test_example_output.csv')

    captured = capsys.readouterr()

    expected_csv = read_csv('example_output.csv')
    actual_csv = read_csv_str(captured.out)

    assert actual_csv == expected_csv
    assert captured.err == ''

    # Clean up
    cleanup()


def test_keepass_csv(capsys):
    '''Two csv files .totp and .htop are generated.'''
    # Arrange
    cleanup()

    # Act
    extract_otp_secret_keys.main(['-q', '-k', 'test_example_keepass_output.csv', 'example_export.txt'])

    # Assert
    expected_totp_csv = read_csv('example_keepass_output.totp.csv')
    expected_hotp_csv = read_csv('example_keepass_output.hotp.csv')
    actual_totp_csv = read_csv('test_example_keepass_output.totp.csv')
    actual_hotp_csv = read_csv('test_example_keepass_output.hotp.csv')

    assert actual_totp_csv == expected_totp_csv
    assert actual_hotp_csv == expected_hotp_csv
    assert not file_exits('test_example_keepass_output.csv')

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == ''

    # Clean up
    cleanup()


def test_keepass_csv_stdout(capsys):
    '''Two csv files .totp and .htop are generated.'''
    # Arrange
    cleanup()

    # Act
    extract_otp_secret_keys.main(['-k', '-', 'test/example_export_only_totp.txt'])

    # Assert
    expected_totp_csv = read_csv('example_keepass_output.totp.csv')
    expected_hotp_csv = read_csv('example_keepass_output.hotp.csv')
    assert not file_exits('test_example_keepass_output.totp.csv')
    assert not file_exits('test_example_keepass_output.hotp.csv')
    assert not file_exits('test_example_keepass_output.csv')

    captured = capsys.readouterr()
    actual_totp_csv = read_csv_str(captured.out)

    assert actual_totp_csv == expected_totp_csv
    assert captured.err == ''

    # Clean up
    cleanup()


def test_single_keepass_csv(capsys):
    '''Does not add .totp or .hotp pre-suffix'''
    # Arrange
    cleanup()

    # Act
    extract_otp_secret_keys.main(['-q', '-k', 'test_example_keepass_output.csv', 'test/example_export_only_totp.txt'])

    # Assert
    expected_totp_csv = read_csv('example_keepass_output.totp.csv')
    actual_totp_csv = read_csv('test_example_keepass_output.csv')

    assert actual_totp_csv == expected_totp_csv
    assert not file_exits('test_example_keepass_output.totp.csv')
    assert not file_exits('test_example_keepass_output.hotp.csv')

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == ''

    # Clean up
    cleanup()


def test_extract_json(capsys):
    # Arrange
    cleanup()

    # Act
    extract_otp_secret_keys.main(['-q', '-j', 'test_example_output.json', 'example_export.txt'])

    # Assert
    expected_json = read_json('example_output.json')
    actual_json = read_json('test_example_output.json')

    assert actual_json == expected_json

    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == ''

    # Clean up
    cleanup()


def test_extract_json_stdout(capsys):
    # Arrange
    cleanup()

    # Act
    extract_otp_secret_keys.main(['-j', '-', 'example_export.txt'])

    # Assert
    expected_json = read_json('example_output.json')
    assert not file_exits('test_example_output.json')
    captured = capsys.readouterr()
    actual_json = read_json_str(captured.out)

    assert actual_json == expected_json
    assert captured.err == ''

    # Clean up
    cleanup()


def test_extract_not_encoded_plus(capsys):
    # Act
    extract_otp_secret_keys.main(['test/test_plus_problem_export.txt'])

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


def test_extract_printqr(capsys):
    # Act
    extract_otp_secret_keys.main(['-p', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stdout = read_file_to_str('test/printqr_output.txt')

    assert captured.out == expected_stdout
    assert captured.err == ''


def test_extract_saveqr(capsys):
    # Arrange
    cleanup()

    # Act
    extract_otp_secret_keys.main(['-q', '-s', 'testout/qr/', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == ''
    assert captured.err == ''

    assert os.path.isfile('testout/qr/1-piraspberrypi-raspberrypi.png')
    assert os.path.isfile('testout/qr/2-piraspberrypi.png')
    assert os.path.isfile('testout/qr/3-piraspberrypi.png')
    assert os.path.isfile('testout/qr/4-piraspberrypi-raspberrypi.png')

    # Clean up
    cleanup()


def test_normalize_bytes():
    assert replace_escaped_octal_utf8_bytes_with_str('Before\\\\302\\\\277\\\\303\nname: enc: \\302\\277\\303\\244\\303\\204\\303\\251\\303\\211?\nAfter') == 'Before\\\\302\\\\277\\\\303\nname: enc: ¿äÄéÉ?\nAfter'


def test_extract_verbose(capsys, relaxed):
    # Act
    extract_otp_secret_keys.main(['-v', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stdout = read_file_to_str('test/print_verbose_output.txt')

    if relaxed or sys.implementation.name == 'pypy':
        print('\nRelaxed mode\n')

        assert replace_escaped_octal_utf8_bytes_with_str(captured.out) == replace_escaped_octal_utf8_bytes_with_str(expected_stdout)
        assert quick_and_dirty_workaround_encoding_problem(captured.out) == quick_and_dirty_workaround_encoding_problem(expected_stdout)
    else:
        assert captured.out == expected_stdout
    assert captured.err == ''


def test_extract_debug(capsys):
    # Act
    extract_otp_secret_keys.main(['-vv', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stdout = read_file_to_str('test/print_verbose_output.txt')

    assert len(captured.out) > len(expected_stdout)
    assert "DEBUG: " in captured.out
    assert captured.err == ''


def test_extract_help(capsys):
    with pytest.raises(SystemExit) as e:
        # Act
        extract_otp_secret_keys.main(['-h'])

    # Assert
    captured = capsys.readouterr()

    assert len(captured.out) > 0
    assert "-h, --help" in captured.out and "--verbose, -v" in captured.out
    assert captured.err == ''
    assert e.type == SystemExit
    assert e.value.code == 0


def test_extract_no_arguments(capsys):
    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secret_keys.main([])

    # Assert
    captured = capsys.readouterr()

    expected_err_msg = 'error: the following arguments are required: infile'

    assert expected_err_msg in captured.err
    assert captured.out == ''
    assert e.value.code == 2
    assert e.type == SystemExit


def test_verbose_and_quiet(capsys):
    with pytest.raises(SystemExit) as e:
        # Act
        extract_otp_secret_keys.main(['-v', '-q', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    assert len(captured.err) > 0
    assert 'error: argument --quiet/-q: not allowed with argument --verbose/-v' in captured.err
    assert captured.out == ''
    assert e.value.code == 2
    assert e.type == SystemExit


def test_wrong_data(capsys):
    with pytest.raises(SystemExit) as e:
        # Act
        extract_otp_secret_keys.main(['test/test_export_wrong_data.txt'])

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


def test_wrong_content(capsys):
    with pytest.raises(SystemExit) as e:
        # Act
        extract_otp_secret_keys.main(['test/test_export_wrong_content.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '''
WARN: line is not a otpauth-migration:// URL
input file: test/test_export_wrong_content.txt
line "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua."
Probably a wrong file was given

ERROR: no data query parameter in input URL
input file: test/test_export_wrong_content.txt
line "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua."
Probably a wrong file was given
'''

    assert captured.out == ''
    assert captured.err == expected_stderr
    assert e.value.code == 1
    assert e.type == SystemExit


def test_wrong_prefix(capsys):
    # Act
    extract_otp_secret_keys.main(['test/test_export_wrong_prefix.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '''
WARN: line is not a otpauth-migration:// URL
input file: test/test_export_wrong_prefix.txt
line "QR-Code:otpauth-migration://offline?data=CjUKEPqlBekzoNEukL7qlsjBCDYSDnBpQHJhc3BiZXJyeXBpGgtyYXNwYmVycnlwaSABKAEwAhABGAEgACjr4JKK%2B%2F%2F%2F%2F%2F8B"
Probably a wrong file was given
'''

    expected_stdout = '''Name:    pi@raspberrypi
Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY
Issuer:  raspberrypi
Type:    totp

'''

    assert captured.out == expected_stdout
    assert captured.err == expected_stderr


def test_add_pre_suffix(capsys):
    assert extract_otp_secret_keys.add_pre_suffix("name.csv", "totp") == "name.totp.csv"
    assert extract_otp_secret_keys.add_pre_suffix("name.csv", "") == "name..csv"
    assert extract_otp_secret_keys.add_pre_suffix("name", "totp") == "name.totp"


@pytest.mark.qreader
def test_img_qr_reader_from_file_happy_path(capsys):
    # Act
    extract_otp_secret_keys.main(['test/test_googleauth_export.png'])

    # Assert
    captured = capsys.readouterr()

    assert captured.out == EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT_PNG
    assert captured.err == ''

@pytest.mark.qreader
def test_img_qr_reader_from_stdin(capsys, monkeypatch):
    # Arrange
    # sys.stdin.buffer should be monkey patched, but it does not work
    monkeypatch.setattr('sys.stdin', read_binary_file_as_stream('test/test_googleauth_export.png'))

    # Act
    extract_otp_secret_keys.main(['='])

    # Assert
    captured = capsys.readouterr()

    expected_stdout =\
'''Name:    Test1:test1@example1.com
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
def test_img_qr_reader_from_stdin_wrong_symbol(capsys, monkeypatch):
    # Arrange
    # sys.stdin.buffer should be monkey patched, but it does not work
    monkeypatch.setattr('sys.stdin', read_binary_file_as_stream('test/test_googleauth_export.png'))

    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secret_keys.main(['-'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '\nBinary input was given in stdin, please use = instead of - as infile argument for images.\n'

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


@pytest.mark.qreader
def test_img_qr_reader_no_qr_code_in_image(capsys):
    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secret_keys.main(['test/lena_std.tif'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '\nERROR: Unable to read QR Code from file.\ninput file: test/lena_std.tif\n'

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


@pytest.mark.qreader
def test_img_qr_reader_nonexistent_file(capsys):
    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secret_keys.main(['test/nonexistent.bmp'])

    # Assert
    captured = capsys.readouterr()

    expected_stderr = '\nERROR: Input file provided is non-existent or not a file.\ninput file: test/nonexistent.bmp\n'

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


def test_non_image_file(capsys):
    # Act
    with pytest.raises(SystemExit) as e:
        extract_otp_secret_keys.main(['test/text_masquerading_as_image.jpeg'])

    # Assert
    captured = capsys.readouterr()
    expected_stderr = '''
WARN: line is not a otpauth-migration:// URL
input file: test/text_masquerading_as_image.jpeg
line "This is just a text file masquerading as an image file."
Probably a wrong file was given

ERROR: no data query parameter in input URL
input file: test/text_masquerading_as_image.jpeg
line "This is just a text file masquerading as an image file."
Probably a wrong file was given
'''

    assert captured.err == expected_stderr
    assert captured.out == ''
    assert e.value.code == 1
    assert e.type == SystemExit


def cleanup():
    remove_files('test_example_*.csv')
    remove_files('test_example_*.json')
    remove_dir_with_files('testout/')


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

EXPECTED_STDOUT_FROM_EXAMPLE_EXPORT_PNG =\
'''Name:    Test1:test1@example1.com
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
