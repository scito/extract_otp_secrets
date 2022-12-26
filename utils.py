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

import csv
import glob
import io
import json
import os
import re
import shutil
import sys


# Ref. https://stackoverflow.com/a/16571630
class Capturing(list):
    '''Capture stdout and stderr
Usage:
with Capturing() as output:
    print("Output")
'''
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio_std = io.StringIO()
        self._stderr = sys.stderr
        sys.stderr = self._stringio_err = io.StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio_std.getvalue().splitlines())
        del self._stringio_std    # free up some memory
        sys.stdout = self._stdout

        self.extend(self._stringio_err.getvalue().splitlines())
        del self._stringio_err    # free up some memory
        sys.stderr = self._stderr


def file_exits(file):
    return os.path.isfile(file)


def remove_file(file):
    if file_exits(file): os.remove(file)


def remove_files(glob_pattern):
    for f in glob.glob(glob_pattern):
        os.remove(f)


def remove_dir_with_files(dir):
    if os.path.exists(dir): shutil.rmtree(dir)


def read_csv(filename):
    """Returns a list of lines."""
    with open(filename, "r", encoding="utf-8", newline='') as infile:
        lines = []
        reader = csv.reader(infile)
        for line in reader:
            lines.append(line)
        return lines


def read_csv_str(str):
    """Returns a list of lines."""
    lines = []
    reader = csv.reader(str.splitlines())
    for line in reader:
        lines.append(line)
    return lines


def read_json(filename):
    """Returns a list or a dictionary."""
    with open(filename, "r", encoding="utf-8") as infile:
        return json.load(infile)


def read_json_str(str):
    """Returns a list or a dictionary."""
    return json.loads(str)


def read_file_to_list(filename):
    """Returns a list of lines."""
    with open(filename, "r", encoding="utf-8") as infile:
        return infile.readlines()


def read_file_to_str(filename):
    """Returns a str."""
    return "".join(read_file_to_list(filename))

def read_binary_file_as_stream(filename):
    """Returns binary file content."""
    with open(filename, "rb",) as infile:
        return io.BytesIO(infile.read())

def replace_escaped_octal_utf8_bytes_with_str(str):
    encoded_name_strings = re.findall(r'name: .*$', str, flags=re.MULTILINE)
    for encoded_name_string in encoded_name_strings:
        escaped_bytes = re.findall(r'((?:\\[0-9]+)+)', encoded_name_string)
        for byte_sequence in escaped_bytes:
            unicode_str = b''.join([int(byte, 8).to_bytes(1, 'little') for byte in byte_sequence.split('\\') if byte]).decode('utf-8')
            print("Replace '{}' by '{}'".format(byte_sequence, unicode_str))
            str = str.replace(byte_sequence, unicode_str)
    return str


def quick_and_dirty_workaround_encoding_problem(str):
    return re.sub(r'name: "encoding: .*$', '', str, flags=re.MULTILINE)
