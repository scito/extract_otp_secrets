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
import csv
import glob
import io
import json
import os
import re
import shutil
import sys
import pathlib
from typing import BinaryIO, Any, Union, List


# Types
# workaround for PYTHON <= 3.9: Workaround for str | pathlib.Path
PathLike = Union[str, pathlib.Path]


# Ref. https://stackoverflow.com/a/16571630
# workaround for PYTHON <= 3.10: class Capturing(list[Any]):
class Capturing(List[Any]):
    '''Capture stdout and stderr
Usage:
with Capturing() as output:
    print("Output")
'''
    # TODO remove type ignore if fixed, see https://github.com/python/mypy/issues/11871, https://stackoverflow.com/questions/72174409/type-hinting-the-return-value-of-a-class-method-that-returns-self
    def __enter__(self):  # type: ignore
        self._stdout = sys.stdout
        sys.stdout = self._stringio_std = io.StringIO()
        self._stderr = sys.stderr
        sys.stderr = self._stringio_err = io.StringIO()
        return self

    def __exit__(self, *args: Any) -> None:
        self.extend(self._stringio_std.getvalue().splitlines())
        del self._stringio_std    # free up some memory
        sys.stdout = self._stdout

        self.extend(self._stringio_err.getvalue().splitlines())
        del self._stringio_err    # free up some memory
        sys.stderr = self._stderr


def file_exits(file: PathLike) -> bool:
    return os.path.isfile(file)


def remove_file(file: PathLike) -> None:
    if file_exits(file): os.remove(file)


def remove_files(glob_pattern: str) -> None:
    for f in glob.glob(glob_pattern):
        os.remove(f)


def remove_dir_with_files(dir: PathLike) -> None:
    if os.path.exists(dir): shutil.rmtree(dir)


def read_csv(filename: str) -> List[List[str]]:
    """Returns a list of lines."""
    with open(filename, "r", encoding="utf-8", newline='') as infile:
        lines: List[List[str]] = []
        reader = csv.reader(infile)
        for line in reader:
            lines.append(line)
        return lines


def read_csv_str(data_str: str) -> List[List[str]]:
    """Returns a list of lines."""
    lines: List[List[str]] = []
    reader = csv.reader(data_str.splitlines())
    for line in reader:
        lines.append(line)
    return lines


def read_json(filename: str) -> Any:
    """Returns a list or a dictionary."""
    with open(filename, "r", encoding="utf-8") as infile:
        return json.load(infile)


def read_json_str(data_str: str) -> Any:
    """Returns a list or a dictionary."""
    return json.loads(data_str)


def read_file_to_list(filename: str) -> List[str]:
    """Returns a list of lines."""
    with open(filename, "r", encoding="utf-8") as infile:
        return infile.readlines()


def read_file_to_str(filename: str) -> str:
    """Returns a str."""
    return "".join(read_file_to_list(filename))


def read_binary_file_as_stream(filename: str) -> BinaryIO:
    """Returns binary file content."""
    with open(filename, "rb",) as infile:
        return io.BytesIO(infile.read())


def replace_escaped_octal_utf8_bytes_with_str(str: str) -> str:
    encoded_name_strings = re.findall(r'name: .*$', str, flags=re.MULTILINE)
    for encoded_name_string in encoded_name_strings:
        escaped_bytes = re.findall(r'((?:\\[0-9]+)+)', encoded_name_string)
        for byte_sequence in escaped_bytes:
            unicode_str = b''.join([int(byte, 8).to_bytes(1, 'little') for byte in byte_sequence.split('\\') if byte]).decode('utf-8')
            print("Replace '{}' by '{}'".format(byte_sequence, unicode_str))
            str = str.replace(byte_sequence, unicode_str)
    return str


def quick_and_dirty_workaround_encoding_problem(str: str) -> str:
    return re.sub(r'name: "encoding: .*$', '', str, flags=re.MULTILINE)


def count_files_in_dir(path: PathLike) -> int:
    return len([name for name in os.listdir(path) if os.path.isfile(os.path.join(path, name))])
