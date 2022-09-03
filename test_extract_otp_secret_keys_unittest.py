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
import csv
import json
import os

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

    def setUp(self):
        self.cleanup()

    def tearDown(self):
        self.cleanup()

    def cleanup(self):
        remove_file('test_example_output.csv')
        remove_file('test_example_output.json')


def remove_file(filename):
    if os.path.exists(filename): os.remove(filename)


def read_csv(filename):
    """Returns a list of lines."""
    with open(filename, "r") as infile:
        lines = []
        reader = csv.reader(infile)
        for line in reader:
            lines.append(line)
        return lines


def read_json(filename):
    """Returns a list or a dictionary."""
    with open(filename, "r") as infile:
        return json.load(infile)


if __name__ == '__main__':
    unittest.main()
