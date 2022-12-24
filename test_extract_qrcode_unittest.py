# Unit test for extract_otp_secret_keys.py

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

import unittest
from utils import Capturing

import extract_otp_secret_keys

class TestQRImageExtract(unittest.TestCase):
    def test_img_qr_reader_happy_path(self):
        with Capturing() as actual_output:
            extract_otp_secret_keys.main(['test/test_googleauth_export.png'])

        expected_output =\
        ['Name:    Test1:test1@example1.com', 'Secret:  JBSWY3DPEHPK3PXP', 'Issuer:  Test1', 'Type:    totp', '',
         'Name:    Test2:test2@example2.com', 'Secret:  JBSWY3DPEHPK3PXQ', 'Issuer:  Test2', 'Type:    totp', '',
         'Name:    Test3:test3@example3.com', 'Secret:  JBSWY3DPEHPK3PXR', 'Issuer:  Test3', 'Type:    totp', '']

        self.assertEqual(actual_output, expected_output)

    def test_img_qr_reader_no_qr_code_in_image(self):
        with Capturing() as actual_output:
            with self.assertRaises(SystemExit) as context:
                extract_otp_secret_keys.main(['test/lena_std.tif'])

        expected_output =\
        ['', 'ERROR: Unable to read QR Code from file.', 'input file: test/lena_std.tif']

        self.assertEqual(actual_output, expected_output)
        self.assertEqual(context.exception.code, 1)

    def test_img_qr_reader_nonexistent_file(self):
        with Capturing() as actual_output:
            with self.assertRaises(SystemExit) as context:
                extract_otp_secret_keys.main(['test/nonexistent.bmp'])

        expected_output =\
        ['', 'ERROR: Input file provided is non-existent or not a file.', 'input file: test/nonexistent.bmp']

        self.assertEqual(actual_output, expected_output)
        self.assertEqual(context.exception.code, 1)

    def test_img_qr_reader_non_image_file(self):
        with Capturing() as actual_output:
            with self.assertRaises(SystemExit) as context:
                extract_otp_secret_keys.main(['test/text_masquerading_as_image.jpeg'])

        expected_output = [
            '',
            'WARN: line is not a otpauth-migration:// URL',
            'input file: test/text_masquerading_as_image.jpeg',
            'line "This is just a text file masquerading as an image file."',
            'Probably a wrong file was given',
            '',
            'ERROR: no data query parameter in input URL',
            'input file: test/text_masquerading_as_image.jpeg',
            'line "This is just a text file masquerading as an image file."',
            'Probably a wrong file was given'
        ]

        self.assertEqual(actual_output, expected_output)
        self.assertEqual(context.exception.code, 1)

    def setUp(self):
        self.cleanup()

    def tearDown(self):
        self.cleanup()

    def cleanup(self):
        pass


if __name__ == '__main__':
    unittest.main()
