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

from utils import read_csv, read_json, remove_file, read_file_to_str

import extract_otp_secret_keys


def test_extract_csv():
    # Arrange
    cleanup()

    # Act
    extract_otp_secret_keys.main(['-q', '-c', 'test_example_output.csv', 'example_export.txt'])

    # Assert
    expected_csv = read_csv('example_output.csv')
    actual_csv = read_csv('test_example_output.csv')

    assert actual_csv == expected_csv

    # Clean up
    cleanup()


def test_extract_json():
    # Arrange
    cleanup()

    # Act
    extract_otp_secret_keys.main(['-q', '-j', 'test_example_output.json', 'example_export.txt'])

    # Assert
    expected_json = read_json('example_output.json')
    actual_json = read_json('test_example_output.json')

    assert actual_json == expected_json

    # Clean up
    cleanup()


def test_extract_stdout(capsys):
    # Act
    extract_otp_secret_keys.main(['example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stdout = '''Name:   pi@raspberrypi
Secret: 7KSQL2JTUDIS5EF65KLMRQIIGY
Issuer: raspberrypi
Type:   OTP_TOTP

Name:   pi@raspberrypi
Secret: 7KSQL2JTUDIS5EF65KLMRQIIGY
Type:   OTP_TOTP

Name:   pi@raspberrypi
Secret: 7KSQL2JTUDIS5EF65KLMRQIIGY
Type:   OTP_TOTP

Name:   pi@raspberrypi
Secret: 7KSQL2JTUDIS5EF65KLMRQIIGY
Issuer: raspberrypi
Type:   OTP_TOTP

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


def test_extract_verbose(capsys):
    # Act
    extract_otp_secret_keys.main(['-v', 'example_export.txt'])

    # Assert
    captured = capsys.readouterr()

    expected_stdout = read_file_to_str('test/print_verbose_output.txt')

    assert captured.out == expected_stdout
    assert captured.err == ''


def cleanup():
    remove_file('test_example_output.csv')
    remove_file('test_example_output.json')
