# Unit test for extract_otp_secrets.py

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

from __future__ import annotations  # workaround for PYTHON <= 3.10

import io
import os
import unittest
from contextlib import redirect_stdout

from utils import (Capturing, count_files_in_dir, read_csv, read_file_to_str,
                   read_json, remove_dir_with_files, remove_file)

import extract_otp_secrets

# Conditional skip example
# if sys.implementation.name == 'pypy' or sys.platform.startswith("win") or sys.version_info < (3, 10):
#             self.skipTest("Avoid encoding problems")


class TestExtract(unittest.TestCase):

    def test_extract_csv(self) -> None:
        extract_otp_secrets.main(['-q', '-c', 'test_example_output.csv', 'example_export.txt'])

        expected_csv = read_csv('example_output.csv')
        actual_csv = read_csv('test_example_output.csv')

        self.assertEqual(actual_csv, expected_csv)

    def test_extract_json(self) -> None:
        extract_otp_secrets.main(['-q', '-j', 'test_example_output.json', 'example_export.txt'])

        expected_json = read_json('example_output.json')
        actual_json = read_json('test_example_output.json')

        self.assertEqual(actual_json, expected_json)

    def test_extract_stdout_1(self) -> None:
        with Capturing() as output:
            extract_otp_secrets.main(['example_export.txt'])

        expected_output = [
            'Name:    pi@raspberrypi',
            'Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY',
            'Issuer:  raspberrypi',
            'Type:    totp',
            '',
            'Name:    pi@raspberrypi',
            'Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY',
            'Type:    totp',
            '',
            'Name:    pi@raspberrypi',
            'Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY',
            'Type:    totp',
            '',
            'Name:    pi@raspberrypi',
            'Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY',
            'Issuer:  raspberrypi',
            'Type:    totp',
            '',
            'Name:    hotp demo',
            'Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY',
            'Type:    hotp',
            'Counter: 4',
            '',
            'Name:    encoding: ¿äÄéÉ? (demo)',
            'Secret:  7KSQL2JTUDIS5EF65KLMRQIIGY',
            'Type:    totp',
            ''
        ]
        self.assertEqual(output, expected_output)

    # Ref for capturing https://stackoverflow.com/a/40984270
    def test_extract_stdout_2(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            extract_otp_secrets.main(['example_export.txt'])
        actual_output = out.getvalue()

        expected_output = '''Name:    pi@raspberrypi
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
        self.assertEqual(actual_output, expected_output)

    def test_extract_not_encoded_plus(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            extract_otp_secrets.main(['tests/data/test_plus_problem_export.txt'])
        actual_output = out.getvalue()

        expected_output = '''Name:    SerenityLabs:test1@serenitylabs.co.uk
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
        self.assertEqual(actual_output, expected_output)

    def test_extract_printqr(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            extract_otp_secrets.main(['-p', 'example_export.txt'])
        actual_output = out.getvalue()

        expected_output = read_file_to_str('tests/data/printqr_output.txt')

        self.assertEqual(actual_output, expected_output)

    def test_extract_saveqr(self) -> None:
        extract_otp_secrets.main(['-q', '-s', 'testout/qr/', 'example_export.txt'])

        self.assertTrue(os.path.isfile('testout/qr/1-piraspberrypi-raspberrypi.png'))
        self.assertTrue(os.path.isfile('testout/qr/2-piraspberrypi.png'))
        self.assertTrue(os.path.isfile('testout/qr/3-piraspberrypi.png'))
        self.assertTrue(os.path.isfile('testout/qr/4-piraspberrypi-raspberrypi.png'))
        self.assertTrue(os.path.isfile('testout/qr/5-hotpdemo.png'))
        self.assertTrue(os.path.isfile('testout/qr/6-encodingäÄéÉdemo.png'))
        self.assertEqual(count_files_in_dir('testout/qr'), 6)

    def test_extract_debug(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            extract_otp_secrets.main(['-vvv', 'example_export.txt'])
        actual_output = out.getvalue()

        expected_stdout = read_file_to_str('tests/data/print_verbose_output.txt')

        self.assertGreater(len(actual_output), len(expected_stdout))
        self.assertTrue("DEBUG: " in actual_output)

    def test_extract_help_1(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            try:
                extract_otp_secrets.main(['-h'])
                self.fail("Must abort")
            except SystemExit as e:
                self.assertEqual(e.code, 0)

        actual_output = out.getvalue()

        self.assertGreater(len(actual_output), 0)
        self.assertTrue("-h, --help" in actual_output and "-v, --verbose" in actual_output)

    def test_extract_help_2(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            with self.assertRaises(SystemExit) as context:
                extract_otp_secrets.main(['-h'])

        actual_output = out.getvalue()

        self.assertGreater(len(actual_output), 0)
        self.assertTrue("-h, --help" in actual_output and "-v, --verbose" in actual_output)
        self.assertEqual(context.exception.code, 0)

    def test_extract_help_3(self) -> None:
        with Capturing() as actual_output:
            with self.assertRaises(SystemExit) as context:
                extract_otp_secrets.main(['-h'])

        self.assertGreater(len(actual_output), 0)
        self.assertTrue("-h, --help" in "\n".join(actual_output) and "-v, --verbose" in "\n".join(actual_output))
        self.assertEqual(context.exception.code, 0)

    def setUp(self) -> None:
        self.cleanup()

    def tearDown(self) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        remove_file('test_example_output.csv')
        remove_file('test_example_output.json')
        remove_dir_with_files('testout/')


if __name__ == '__main__':
    unittest.main()
