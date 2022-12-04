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

from utils import read_csv, read_json, remove_files, remove_dir_with_files, read_file_to_str, file_exits
from os import path
from pytest import raises

import extract_otp_secret_keys


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


def test_extract_stdout(capsys):
    # Act
    extract_otp_secret_keys.main(['example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stdout = '''Name:    pi@raspberrypi
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

'''

    assert captured.out == expected_stdout
    assert captured.err == ''


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

    assert path.isfile('testout/qr/1-piraspberrypi-raspberrypi.png')
    assert path.isfile('testout/qr/2-piraspberrypi.png')
    assert path.isfile('testout/qr/3-piraspberrypi.png')
    assert path.isfile('testout/qr/4-piraspberrypi-raspberrypi.png')

    # Clean up
    cleanup()


def test_extract_verbose(capsys):
    # Act
    extract_otp_secret_keys.main(['-v', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stdout = read_file_to_str('test/print_verbose_output.txt')

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
    with raises(SystemExit) as pytest_wrapped_e:
        # Act
        extract_otp_secret_keys.main(['-h'])

    # Assert
    captured = capsys.readouterr()

    assert len(captured.out) > 0
    assert "-h, --help" in captured.out and "--verbose, -v" in captured.out
    assert captured.err == ''
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0


def test_verbose_and_quiet(capsys):
    with raises(SystemExit) as pytest_wrapped_e:
        # Act
        extract_otp_secret_keys.main(['-v', '-q', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    assert len(captured.out) > 0
    assert 'The arguments --verbose and --quiet are mutually exclusive.' in captured.out


def test_add_pre_suffix(capsys):
    assert extract_otp_secret_keys.add_pre_suffix("name.csv", "totp") == "name.totp.csv"
    assert extract_otp_secret_keys.add_pre_suffix("name.csv", "") == "name..csv"
    assert extract_otp_secret_keys.add_pre_suffix("name", "totp") == "name.totp"


def cleanup():
    remove_files('test_example_*.csv')
    remove_files('test_example_*.json')
    remove_dir_with_files('testout/')
