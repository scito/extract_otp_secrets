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
import json
import os
import shutil
from io import StringIO
import sys
import glob


# Ref. https://stackoverflow.com/a/16571630
class Capturing(list):
    '''Capture stdout and stderr
Usage:
with Capturing() as output:
    print("Output")
'''
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout


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


def read_file_to_list(filename):
    """Returns a list of lines."""
    with open(filename, "r") as infile:
        return infile.readlines()


def read_file_to_str(filename):
    """Returns a str."""
    return "".join(read_file_to_list(filename))
