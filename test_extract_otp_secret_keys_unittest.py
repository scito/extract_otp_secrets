# Unit test for extract_otp_secret_keys.py

# Run tests:
# python -m unittest

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

import unittest
import io
from contextlib import redirect_stdout
from utils import read_csv, read_json, remove_file, Capturing, read_file_to_str

import extract_otp_secret_keys


class TestExtract(unittest.TestCase):

    def test_extract_csv(self):
        extract_otp_secret_keys.main(['-q', '-c', 'test_example_output.csv', 'example_export.txt'])

        expected_csv = read_csv('example_output.csv')
        actual_csv = read_csv('test_example_output.csv')

        self.assertEqual(actual_csv, expected_csv)

    def test_extract_json(self):
        extract_otp_secret_keys.main(['-q', '-j', 'test_example_output.json', 'example_export.txt'])

        expected_json = read_json('example_output.json')
        actual_json = read_json('test_example_output.json')

        self.assertEqual(actual_json, expected_json)

    def test_extract_stdout_1(self):
        with Capturing() as output:
            extract_otp_secret_keys.main(['example_export.txt'])

        expected_output = [
            'Name:   pi@raspberrypi',
            'Secret: 7KSQL2JTUDIS5EF65KLMRQIIGY',
            'Issuer: raspberrypi',
            'Type:   OTP_TOTP',
            '',
            'Name:   pi@raspberrypi',
            'Secret: 7KSQL2JTUDIS5EF65KLMRQIIGY',
            'Type:   OTP_TOTP',
            '',
            'Name:   pi@raspberrypi',
            'Secret: 7KSQL2JTUDIS5EF65KLMRQIIGY',
            'Type:   OTP_TOTP',
            '',
            'Name:   pi@raspberrypi',
            'Secret: 7KSQL2JTUDIS5EF65KLMRQIIGY',
            'Issuer: raspberrypi',
            'Type:   OTP_TOTP',
            ''
        ]
        self.assertEqual(output, expected_output)

    # Ref for capturing https://stackoverflow.com/a/40984270
    def test_extract_stdout_2(self):
        out = io.StringIO()
        with redirect_stdout(out):
            extract_otp_secret_keys.main(['example_export.txt'])
        actual_output = out.getvalue()

        expected_output = '''Name:   pi@raspberrypi
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
        self.assertEqual(actual_output, expected_output)

    def test_extract_not_encoded_plus(self):
        out = io.StringIO()
        with redirect_stdout(out):
            extract_otp_secret_keys.main(['test/test_plus_problem_export.txt'])
        actual_output = out.getvalue()

        expected_output = '''Name:   SerenityLabs:test1@serenitylabs.co.uk
Secret: A4RFDYMF4GSLUIBQV4ZP67OJEZ2XUQVM
Issuer: SerenityLabs
Type:   OTP_TOTP

Name:   SerenityLabs:test2@serenitylabs.co.uk
Secret: SCDDZ7PW5MOZLE3PQCAZM7L4S35K3UDX
Issuer: SerenityLabs
Type:   OTP_TOTP

Name:   SerenityLabs:test3@serenitylabs.co.uk
Secret: TR76272RVYO6EAEY2FX7W7R7KUDEGPJ4
Issuer: SerenityLabs
Type:   OTP_TOTP

Name:   SerenityLabs:test4@serenitylabs.co.uk
Secret: N2ILWSXSJUQUB7S6NONPJSC62NPG7EXN
Issuer: SerenityLabs
Type:   OTP_TOTP

'''
        self.assertEqual(actual_output, expected_output)

    def test_extract_printqr(self):
        out = io.StringIO()
        with redirect_stdout(out):
            extract_otp_secret_keys.main(['-p', 'example_export.txt'])
        actual_output = out.getvalue()

        expected_output = read_file_to_str('test/printqr_output.txt')

        self.assertEqual(actual_output, expected_output)

    def test_extract_verbose(self):
        out = io.StringIO()
        with redirect_stdout(out):
            extract_otp_secret_keys.main(['-v', 'example_export.txt'])
        actual_output = out.getvalue()

        expected_output = read_file_to_str('test/print_verbose_output.txt')

        self.assertEqual(actual_output, expected_output)

    def setUp(self):
        self.cleanup()

    def tearDown(self):
        self.cleanup()

    def cleanup(self):
        remove_file('test_example_output.csv')
        remove_file('test_example_output.json')


if __name__ == '__main__':
    unittest.main()
