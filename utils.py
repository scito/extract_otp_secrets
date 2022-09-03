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
