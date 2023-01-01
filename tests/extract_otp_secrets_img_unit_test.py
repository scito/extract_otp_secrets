# Unit test for extract_otp_secrets.py

# Run tests:
# python -m unittest

# Author: sssudame

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
import unittest

import extract_otp_secrets
from utils import Capturing


class TestQRImageExtract(unittest.TestCase):
    def test_img_qr_reader_happy_path(self) -> None:
        with Capturing() as actual_output:
            extract_otp_secrets.main(['tests/data/test_googleauth_export.png'])

        expected_output =\
            ['Name:    Test1:test1@example1.com', 'Secret:  JBSWY3DPEHPK3PXP', 'Issuer:  Test1', 'Type:    totp', '',
             'Name:    Test2:test2@example2.com', 'Secret:  JBSWY3DPEHPK3PXQ', 'Issuer:  Test2', 'Type:    totp', '',
             'Name:    Test3:test3@example3.com', 'Secret:  JBSWY3DPEHPK3PXR', 'Issuer:  Test3', 'Type:    totp', '']

        self.assertEqual(actual_output, expected_output)

    def test_img_qr_reader_no_qr_code_in_image(self) -> None:
        with Capturing() as actual_output:
            with self.assertRaises(SystemExit) as context:
                extract_otp_secrets.main(['-n', 'tests/data/lena_std.tif'])

        expected_output = ['', 'ERROR: Unable to read QR Code from file.', 'input file: tests/data/lena_std.tif']

        self.assertEqual(actual_output, expected_output)
        self.assertEqual(context.exception.code, 1)

    def test_img_qr_reader_nonexistent_file(self) -> None:
        with Capturing() as actual_output:
            with self.assertRaises(SystemExit) as context:
                extract_otp_secrets.main(['-n', 'nonexistent.bmp'])

        expected_output = ['', 'ERROR: Input file provided is non-existent or not a file.', 'input file: nonexistent.bmp']

        self.assertEqual(actual_output, expected_output)
        self.assertEqual(context.exception.code, 1)

    def test_img_qr_reader_non_image_file(self) -> None:
        with Capturing() as actual_output:
            extract_otp_secrets.main(['-n', 'tests/data/text_masquerading_as_image.jpeg'])

        expected_output = [
            '',
            'WARN: input is not a otpauth-migration:// url',
            'source: tests/data/text_masquerading_as_image.jpeg',
            "input: This is just a text file masquerading as an image file.",
            'Maybe a wrong file was given',
            '',
            'ERROR: could not parse query parameter in input url',
            'source: tests/data/text_masquerading_as_image.jpeg',
            "url: This is just a text file masquerading as an image file.",
        ]

        self.assertEqual(actual_output, expected_output)

    def setUp(self) -> None:
        self.cleanup()

    def tearDown(self) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        pass


if __name__ == '__main__':
    unittest.main()
