# Extract one time password (OTP) secrets from QR codes exported by two-factor authentication (2FA) apps such as "Google Authenticator"
#
# For more information, see README.md
#
# Source code available on https://github.com/scito/extract_otp_secrets
#
# Technical background:
# The export QR code from "Google Authenticator" contains the URL "otpauth-migration://offline?data=...".
# The data parameter is a base64 encoded proto3 message (Google Protocol Buffers).
#
# Command for regeneration of Python code from proto3 message definition file (only necessary in case of changes of the proto3 message definition):
# protoc --plugin=protoc-gen-mypy=path/to/protoc-gen-mypy --python_out=src/protobuf_generated_python --mypy_out=src/protobuf_generated_python --proto_path=src google_auth.proto
#
# References:
# Proto3 documentation: https://developers.google.com/protocol-buffers/docs/pythontutorial
# Template code: https://github.com/beemdevelopment/Aegis/pull/406

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

import argparse
import base64
import csv
import fileinput
import json
import os
import re
import sys
import urllib.parse as urlparse
from enum import Enum, IntEnum
from typing import Any, List, Optional, TextIO, Tuple, Union

# workaround for PYTHON <= 3.7: compatibility
if sys.version_info >= (3, 8):
    from typing import Final, TypedDict
else:
    from typing_extensions import Final, TypedDict

from qrcode import QRCode  # type: ignore

import protobuf_generated_python.google_auth_pb2 as pb
import colorama

debug_mode = '-d' in sys.argv[1:] or '--debug' in sys.argv[1:]

try:
    import cv2  # type: ignore # TODO use cv2 types if available

    import numpy as np  # TODO use numpy types if available

    try:
        import pyzbar.pyzbar as zbar  # type: ignore
        from qreader import QReader  # type: ignore
    except ImportError as e:
        print(f"""
ERROR: Cannot import QReader module. This problem is probably due to the missing zbar shared library.
On Linux and macOS libzbar0 must be installed.
See in README.md for the installation of the libzbar0.
Exception: {e}\n""", file=sys.stderr)
        raise e

    # Types
    # workaround for PYTHON <= 3.9: Final[tuple[int]]
    ColorBGR = Tuple[int, int, int]  # RGB Color specified as Blue, Green, Red
    Point = Tuple[int, int]

    # CV2 camera capture constants
    FONT: Final[int] = cv2.FONT_HERSHEY_PLAIN
    FONT_SCALE: Final[float] = 1.3
    FONT_THICKNESS: Final[int] = 1
    FONT_LINE_STYLE: Final[int] = cv2.LINE_AA
    FONT_COLOR: Final[ColorBGR] = (255, 0, 0)
    BOX_THICKNESS: Final[int] = 5
    # workaround for PYTHON <= 3.7: must use () for assignments
    WINDOW_X: Final[int] = 0
    WINDOW_Y: Final[int] = 1
    WINDOW_WIDTH: Final[int] = 2
    WINDOW_HEIGHT: Final[int] = 3
    TEXT_WIDTH: Final[int] = 0
    TEXT_HEIGHT: Final[int] = 1
    BORDER: Final[int] = 5
    START_Y: Final[int] = 20
    START_POS_TEXT: Final[Point] = (BORDER, START_Y)
    NORMAL_COLOR: Final[ColorBGR] = (255, 0, 255)
    SUCCESS_COLOR: Final[ColorBGR] = (0, 255, 0)
    FAILURE_COLOR: Final[ColorBGR] = (0, 0, 255)
    CHAR_DX: Final[int] = (lambda text: cv2.getTextSize(text, FONT, FONT_SCALE, FONT_THICKNESS)[0][TEXT_WIDTH] // len(text))("28 QR codes capturedMMM")
    FONT_DY: Final[int] = cv2.getTextSize("M", FONT, FONT_SCALE, FONT_THICKNESS)[0][TEXT_HEIGHT] + 5
    WINDOW_NAME: Final[str] = "Extract OTP Secrets: Capture QR Codes from Camera"

    TextPosition = Enum('TextPosition', ['LEFT', 'RIGHT'])

    qreader_available = True
except ImportError as e:
    qreader_available = False
    if debug_mode:
        raise e

# Workaround for PYTHON <= 3.9: Union[int, None] used instead of int | None

# Types
Args = argparse.Namespace
OtpUrl = str
# workaround for PYTHON <= 3.7: Otp = TypedDict('Otp', {'name': str, 'secret': str, 'issuer': str, 'type': str, 'counter': int | None, 'url': OtpUrl})
Otp = TypedDict('Otp', {'name': str, 'secret': str, 'issuer': str, 'type': str, 'counter': Union[int, None], 'url': OtpUrl})
# workaround for PYTHON <= 3.9: Otps = list[Otp]
Otps = List[Otp]
# workaround for PYTHON <= 3.9: OtpUrls = list[OtpUrl]
OtpUrls = List[OtpUrl]

QRMode = Enum('QRMode', ['ZBAR', 'QREADER', 'QREADER_DEEP', 'CV2', 'CV2_WECHAT'], start=0)
LogLevel = IntEnum('LogLevel', ['QUIET', 'NORMAL', 'VERBOSE', 'MORE_VERBOSE', 'DEBUG'], start=-1)


# Constants
CAMERA: Final[str] = 'camera'

# Global variable declaration
verbose: IntEnum = LogLevel.NORMAL
quiet: bool = False
colored: bool = True


def sys_main() -> None:
    main(sys.argv[1:])


def main(sys_args: list[str]) -> None:
    # allow to use sys.stdout with with (avoid closing)
    sys.stdout.close = lambda: None  # type: ignore
    # set encoding to utf-8, needed for Windows
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
        sys.stderr.reconfigure(encoding='utf-8')  # type: ignore
    except AttributeError:  # '_io.StringIO' object has no attribute 'reconfigure'
        # StringIO in tests do not have all attributes, ignore it
        pass

    args = parse_args(sys_args)

    if colored:
        colorama.just_fix_windows_console()

    if args.debug:
        sys.exit(0 if do_debug_checks() else 1)

    otps = extract_otps(args)
    write_csv(args, otps)
    write_keepass_csv(args, otps)
    write_json(args, otps)


def parse_args(sys_args: list[str]) -> Args:
    global verbose, quiet, colored
    description_text = "Extracts one time password (OTP) secrets from QR codes exported by two-factor authentication (2FA) apps"
    if qreader_available:
        description_text += "\nIf no infiles are provided, a GUI window starts and QR codes are captured from the camera."
    example_text = """examples:
python extract_otp_secrets.py
python extract_otp_secrets.py example_*.txt
python extract_otp_secrets.py - < example_export.txt
python extract_otp_secrets.py --csv - example_*.png | tail -n+2
python extract_otp_secrets.py = < example_export.png"""

    arg_parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=32),
                                         description=description_text,
                                         epilog=example_text)
    arg_parser.add_argument('infile', help="""a) file or - for stdin with 'otpauth-migration://...' URLs separated by newlines, lines starting with # are ignored;
b) image file containing a QR code or = for stdin for an image containing a QR code""", nargs='*' if qreader_available else '+')
    arg_parser.add_argument('--csv', '-c', help='export csv file or - for stdout', metavar=('FILE'))
    arg_parser.add_argument('--keepass', '-k', help='export totp/hotp csv file(s) for KeePass, - for stdout', metavar=('FILE'))
    arg_parser.add_argument('--json', '-j', help='export json file or - for stdout', metavar=('FILE'))
    arg_parser.add_argument('--printqr', '-p', help='print QR code(s) as text to the terminal (requires qrcode module)', action='store_true')
    arg_parser.add_argument('--saveqr', '-s', help='save QR code(s) as images to the given folder (requires qrcode module)', metavar=('DIR'))
    if qreader_available:
        arg_parser.add_argument('--camera', '-C', help='camera number of system (default camera: 0)', default=0, type=int, metavar=('NUMBER'))
        arg_parser.add_argument('--qr', '-Q', help=f'QR reader (default: {QRMode.ZBAR.name})', type=str, choices=[mode.name for mode in QRMode], default=QRMode.ZBAR.name)
    arg_parser.add_argument('-i', '--ignore', help='ignore duplicate otps', action='store_true')
    arg_parser.add_argument('--no-color', '-n', help='do not use ANSI colors in console output', action='store_true')
    output_group = arg_parser.add_mutually_exclusive_group()
    output_group.add_argument('-d', '--debug', help='enter debug mode, do checks and quit', action='count')
    output_group.add_argument('-v', '--verbose', help='verbose output', action='count')
    output_group.add_argument('-q', '--quiet', help='no stdout output, except output set by -', action='store_true')
    args = arg_parser.parse_args(sys_args)
    colored = not args.no_color
    if args.csv == '-' or args.json == '-' or args.keepass == '-':
        args.quiet = args.q = True

    verbose = args.verbose if args.verbose else LogLevel.NORMAL
    if args.debug:
        verbose = LogLevel.DEBUG
        log_debug('Debug mode start')
    quiet = True if args.quiet else False
    if verbose: print(f"QReader installed: {qreader_available}")
    if qreader_available:
        if verbose >= LogLevel.VERBOSE: print(f"CV2 version: {cv2.__version__}")
        if verbose: print(f"QR reading mode: {args.qr}\n")

    return args


def extract_otps(args: Args) -> Otps:
    if not args.infile:
        return extract_otps_from_camera(args)
    else:
        return extract_otps_from_files(args)


def get_color(new_otps_count: int, otp_url: str) -> ColorBGR:
    if new_otps_count:
        return SUCCESS_COLOR
    else:
        if otp_url:
            return FAILURE_COLOR
        else:
            return NORMAL_COLOR


# TODO use cv2 types if available
def cv2_draw_box(img: Any, raw_pts: Any, color: ColorBGR) -> Any:
    pts = np.array([raw_pts], np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.polylines(img, [pts], True, color, BOX_THICKNESS)
    return pts


# TODO use cv2 types if available
def cv2_print_text(img: Any, text: str, line_number: int, position: TextPosition, color: ColorBGR, opposite_len: Optional[int] = None) -> None:
    window_dim = cv2.getWindowImageRect(WINDOW_NAME)
    out_text = text
    if opposite_len:
        text_dim, _ = cv2.getTextSize(out_text, FONT, FONT_SCALE, FONT_THICKNESS)
        actual_width = text_dim[TEXT_WIDTH] + opposite_len * CHAR_DX + 4 * BORDER
        if actual_width >= window_dim[WINDOW_WIDTH]:
            out_text = out_text[:(window_dim[WINDOW_WIDTH] - actual_width) // CHAR_DX] + '.'
    text_dim, _ = cv2.getTextSize(out_text, FONT, FONT_SCALE, FONT_THICKNESS)
    if position == TextPosition.LEFT:
        pos = BORDER, START_Y + line_number * FONT_DY
    else:
        pos = window_dim[WINDOW_WIDTH] - text_dim[TEXT_WIDTH] - BORDER, START_Y + line_number * FONT_DY

    cv2.putText(img, out_text, pos, FONT, FONT_SCALE, color, FONT_THICKNESS, FONT_LINE_STYLE)


def extract_otps_from_camera(args: Args) -> Otps:
    if verbose: print("Capture QR codes from camera")
    otp_urls: OtpUrls = []
    otps: Otps = []

    qr_mode = QRMode[args.qr]

    cam = cv2.VideoCapture(args.camera)
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)

    qreader = QReader()
    cv2_qr = cv2.QRCodeDetector()
    cv2_qr_wechat = cv2.wechat_qrcode.WeChatQRCode()
    while True:
        success, img = cam.read()
        new_otps_count = 0
        if not success:
            log_error("Failed to capture image from camera")
            break
        try:
            if qr_mode in [QRMode.QREADER, QRMode.QREADER_DEEP]:
                found, bbox = qreader.detect(img)
                if qr_mode == QRMode.QREADER_DEEP:
                    otp_url = qreader.detect_and_decode(img, True)
                elif qr_mode == QRMode.QREADER:
                    otp_url = qreader.decode(img, bbox) if found else None
                if otp_url:
                    new_otps_count = extract_otps_from_otp_url(otp_url, otp_urls, otps, args)
                if found:
                    cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), get_color(new_otps_count, otp_url), BOX_THICKNESS)
            elif qr_mode == QRMode.ZBAR:
                for qrcode in zbar.decode(img):
                    otp_url = qrcode.data.decode('utf-8')
                    new_otps_count = extract_otps_from_otp_url(otp_url, otp_urls, otps, args)
                    cv2_draw_box(img, [qrcode.polygon], get_color(new_otps_count, otp_url))
            elif qr_mode in [QRMode.CV2, QRMode.CV2_WECHAT]:
                if QRMode.CV2:
                    otp_url, raw_pts, _ = cv2_qr.detectAndDecode(img)
                else:
                    otp_url, raw_pts = cv2_qr_wechat.detectAndDecode(img)
                if raw_pts is not None:
                    if otp_url:
                        new_otps_count = extract_otps_from_otp_url(otp_url, otp_urls, otps, args)
                    cv2_draw_box(img, raw_pts, get_color(new_otps_count, otp_url))
            else:
                abort(f"Invalid QReader mode: {qr_mode.name}")
        except Exception as e:
            log_error(f'An error occured during QR detection and decoding for QR reader {qr_mode}. Changed to the next QR reader.', e)
            qr_mode = next_qr_mode(qr_mode)
            continue

        cv2_print_text(img, f"Mode: {qr_mode.name} (Hit space to change)", 0, TextPosition.LEFT, FONT_COLOR, 20)
        cv2_print_text(img, "Hit ESC to quit", 1, TextPosition.LEFT, FONT_COLOR, 17)

        cv2_print_text(img, f"{len(otp_urls)} QR code{'s'[:len(otp_urls) != 1]} captured", 0, TextPosition.RIGHT, FONT_COLOR)
        cv2_print_text(img, f"{len(otps)} otp{'s'[:len(otps) != 1]} extracted", 1, TextPosition.RIGHT, FONT_COLOR)

        cv2.imshow(WINDOW_NAME, img)

        quit, qr_mode = cv2_handle_pressed_keys(qr_mode)
        if quit:
            break

    cam.release()
    cv2.destroyAllWindows()

    return otps


def cv2_handle_pressed_keys(qr_mode: QRMode) -> Tuple[bool, QRMode]:
    key = cv2.waitKey(1) & 0xFF
    quit = False
    if key == 27 or key == ord('q') or key == 13:
        # ESC or Enter or q pressed
        quit = True
    elif key == 32:
        qr_mode = next_qr_mode(qr_mode)
        if verbose >= LogLevel.MORE_VERBOSE: print(f"QR reading mode: {qr_mode}")
    if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
        # Window close clicked
        quit = True
    return quit, qr_mode


def extract_otps_from_otp_url(otp_url: str, otp_urls: OtpUrls, otps: Otps, args: Args) -> int:
    '''Returns -1 if opt_url was already added.'''
    if otp_url and verbose >= LogLevel.VERBOSE: print(otp_url)
    if not otp_url:
        return 0
    if otp_url not in otp_urls:
        new_otps_count = extract_otp_from_otp_url(otp_url, otps, len(otp_urls), CAMERA, args)
        if new_otps_count:
            otp_urls.append(otp_url)
        if verbose: print(f"Extracted {new_otps_count} otp{'s'[:len(otps) != 1]}. {len(otps)} otp{'s'[:len(otps) != 1]} from {len(otp_urls)} QR code{'s'[:len(otp_urls) != 1]} extracted")
        return new_otps_count
    return -1


def extract_otps_from_files(args: Args) -> Otps:
    otps: Otps = []

    files_count = urls_count = otps_count = 0
    if verbose: print(f"Input files: {args.infile}")
    for infile in args.infile:
        if verbose >= LogLevel.MORE_VERBOSE: log_verbose(f"Processing infile {infile}")
        files_count += 1
        for line in get_otp_urls_from_file(infile, args):
            if verbose >= LogLevel.MORE_VERBOSE: log_verbose(line)
            if line.startswith('#') or line == '': continue
            urls_count += 1
            otps_count += extract_otp_from_otp_url(line, otps, urls_count, infile, args)
    if verbose: print(f"Extracted {otps_count} otp{'s'[:otps_count != 1]} from {urls_count} otp url{'s'[:urls_count != 1]} by reading {files_count} infile{'s'[:files_count != 1]}")
    return otps


def get_otp_urls_from_file(filename: str, args: Args) -> OtpUrls:
    # stdin stream cannot be rewinded, thus distinguish, use - for utf-8 stdin and = for binary image stdin
    if filename != '=':
        check_file_exists(filename)
        lines = read_lines_from_text_file(filename)
        if lines or filename == '-':
            return lines

    # could not process text file, try reading as image
    if filename != '-' and qreader_available:
        return convert_img_to_otp_urls(filename, args)

    return []


def read_lines_from_text_file(filename: str) -> list[str]:
    if verbose >= LogLevel.DEBUG: print(f"Reading lines of {filename}")
    # workaround for PYTHON <= 3.9 support encoding
    if sys.version_info >= (3, 10):
        finput = fileinput.input(filename, encoding='utf-8')
    else:
        finput = fileinput.input(filename)
    try:
        lines = []
        for line in (line.strip() for line in finput):
            if verbose >= LogLevel.DEBUG: log_verbose(line)
            if is_binary(line):
                abort("Binary input was given in stdin, please use = instead of - as infile argument for images.")
            # unfortunately yield line leads to random test fails
            lines.append(line)
        if not lines:
            log_warn(f"{filename.replace('-', 'stdin')} is empty")
    except UnicodeDecodeError as e:
        if filename == '-':
            abort("Unable to open text file form stdin. "
                  "In case you want read an image file from stdin, you must use '=' instead of '-'.", e)
        else:  # The file is probably an image, process below
            return []
    finally:
        finput.close()
    return lines


def extract_otp_from_otp_url(otpauth_migration_url: str, otps: Otps, urls_count: int, infile: str, args: Args) -> int:
    payload = get_payload_from_otp_url(otpauth_migration_url, urls_count, infile)

    if not payload:
        return 0

    new_otps_count = 0
    # pylint: disable=no-member
    for raw_otp in payload.otp_parameters:
        if verbose: print(f"\n{len(otps) + 1}. Secret")
        secret = convert_secret_from_bytes_to_base32_str(raw_otp.secret)
        if verbose >= LogLevel.DEBUG: log_debug('OTP enum type:', get_enum_name_by_number(raw_otp, 'type'))
        otp_type = get_otp_type_str_from_code(raw_otp.type)
        otp_url = build_otp_url(secret, raw_otp)
        otp: Otp = {
            "name": raw_otp.name,
            "secret": secret,
            "issuer": raw_otp.issuer,
            "type": otp_type,
            "counter": raw_otp.counter if raw_otp.type == 1 else None,
            "url": otp_url
        }
        if otp not in otps or not args.ignore:
            otps.append(otp)
            new_otps_count += 1
            if not quiet:
                print_otp(otp)
            if args.printqr:
                print_qr(args, otp_url)
            if args.saveqr:
                save_qr(otp, args, len(otps))
            if not quiet:
                print()
        elif args.ignore and not quiet:
            eprint(f"Ignored duplicate otp: {otp['name']}", f" / {otp['issuer']}\n" if otp['issuer'] else '\n', sep='')

    return new_otps_count


def convert_img_to_otp_urls(filename: str, args: Args) -> OtpUrls:
    if verbose: print(f"Reading image {filename}")
    try:
        if filename != '=':
            img = cv2.imread(filename)
        else:
            try:
                stdin = sys.stdin.buffer.read()
            except AttributeError:
                # Workaround for pytest, since pytest cannot monkeypatch sys.stdin.buffer
                stdin = sys.stdin.read()  # type: ignore # Workaround for pytest fixtures
            if not stdin:
                log_warn("stdin is empty")
            try:
                img_array = np.frombuffer(stdin, dtype='uint8')
            except TypeError as e:
                abort("Cannot read binary stdin buffer.", e)
            if not img_array.size:
                return []
            img = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)

        if img is None:
            abort(f"Unable to open file for reading.\ninput file: {filename}")

        qr_mode = QRMode[args.qr]
        otp_urls = decode_qr_img_otp_urls(img, qr_mode)
        if len(otp_urls) == 0:
            abort(f"Unable to read QR Code from file.\ninput file: {filename}")
    except Exception as e:
        abort(f"Encountered exception\ninput file: {filename}", e)
    return otp_urls


def decode_qr_img_otp_urls(img: Any, qr_mode: QRMode) -> OtpUrls:
    otp_urls: OtpUrls = []
    if qr_mode in [QRMode.QREADER, QRMode.QREADER_DEEP]:
        otp_url = QReader().detect_and_decode(img, qr_mode == QRMode.QREADER_DEEP)
        otp_urls.append(otp_url)
    elif qr_mode == QRMode.CV2:
        otp_url, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
        otp_urls.append(otp_url)
    elif qr_mode == QRMode.CV2_WECHAT:
        otp_url, _ = cv2.wechat_qrcode.WeChatQRCode().detectAndDecode(img)
        otp_urls += list(otp_url)
    elif qr_mode == QRMode.ZBAR:
        qrcodes = zbar.decode(img)
        otp_urls += [qrcode.data.decode('utf-8') for qrcode in qrcodes]
    else:
        assert False, f"Wrong QReader mode {qr_mode.name}"

    return otp_urls


# workaround for PYTHON <= 3.9 use: pb.MigrationPayload | None
def get_payload_from_otp_url(otp_url: str, i: int, source: str) -> Optional[pb.MigrationPayload]:
    '''Extracts the otp migration payload from an otp url. This function is the core of the this appliation.'''
    if not is_opt_url(otp_url, source):
        return None
    parsed_url = urlparse.urlparse(otp_url)
    if verbose >= LogLevel.DEBUG: log_debug(f"parsed_url={parsed_url}")
    try:
        params = urlparse.parse_qs(parsed_url.query, strict_parsing=True)
    except Exception:  # workaround for PYTHON <= 3.10
        params = {}
    if verbose >= LogLevel.DEBUG: log_debug(f"querystring params={params}")
    if 'data' not in params:
        log_error(f"could not parse query parameter in input url\nsource: {source}\nurl: {otp_url}")
        return None
    data_base64 = params['data'][0]
    if verbose >= LogLevel.DEBUG: log_debug(f"data_base64={data_base64}")
    data_base64_fixed = data_base64.replace(' ', '+')
    if verbose >= LogLevel.DEBUG: log_debug(f"data_base64_fixed={data_base64_fixed}")
    data = base64.b64decode(data_base64_fixed, validate=True)
    payload = pb.MigrationPayload()
    try:
        payload.ParseFromString(data)
    except Exception as e:
        abort(f"Cannot decode otpauth-migration migration payload.\n"
              f"data={data_base64}", e)
    if verbose >= LogLevel.DEBUG: log_debug(f"\n{i}. Payload Line", payload, sep='\n')

    return payload


def is_opt_url(otp_url: str, source: str) -> bool:
    if not otp_url.startswith('otpauth-migration://'):
        msg = f"input is not a otpauth-migration:// url\nsource: {source}\ninput: {otp_url}"
        if source == CAMERA:
            log_warn(f"{msg}")
            return False
        else:
            log_warn(f"{msg}\nMaybe a wrong file was given")
    return True


# https://stackoverflow.com/questions/40226049/find-enums-listed-in-python-descriptor-for-protobuf
def get_enum_name_by_number(parent: Any, field_name: str) -> str:
    field_value = getattr(parent, field_name)
    return parent.DESCRIPTOR.fields_by_name[field_name].enum_type.values_by_number.get(field_value).name  # type: ignore # generic code


def get_otp_type_str_from_code(otp_type: int) -> str:
    return 'totp' if otp_type == 2 else 'hotp'


def convert_secret_from_bytes_to_base32_str(bytes: bytes) -> str:
    return str(base64.b32encode(bytes), 'utf-8').replace('=', '')


def build_otp_url(secret: str, raw_otp: pb.MigrationPayload.OtpParameters) -> str:
    url_params = {'secret': secret}
    if raw_otp.type == 1: url_params['counter'] = str(raw_otp.counter)
    if raw_otp.issuer: url_params['issuer'] = raw_otp.issuer
    otp_url = f"otpauth://{get_otp_type_str_from_code(raw_otp.type)}/{urlparse.quote(raw_otp.name)}?" + urlparse.urlencode(url_params)
    return otp_url


def print_otp(otp: Otp) -> None:
    print(f"Name:    {otp['name']}")
    print(f"Secret:  {otp['secret']}")
    if otp['issuer']: print(f"Issuer:  {otp['issuer']}")
    print(f"Type:    {otp['type']}")
    if otp['type'] == 'hotp':
        print(f"Counter: {otp['counter']}")
    if verbose:
        print(otp['url'])


def save_qr(otp: Otp, args: Args, j: int) -> str:
    dir = args.saveqr
    if not (os.path.exists(dir)): os.makedirs(dir, exist_ok=True)
    pattern = re.compile(r'[\W_]+')
    file_otp_name = pattern.sub('', otp['name'])
    file_otp_issuer = pattern.sub('', otp['issuer'])
    save_qr_file(args, otp['url'], f"{dir}/{j}-{file_otp_name}{'-' + file_otp_issuer if file_otp_issuer else ''}.png")
    return file_otp_name


def save_qr_file(args: Args, otp_url: OtpUrl, name: str) -> None:
    qr = QRCode()
    qr.add_data(otp_url)
    img = qr.make_image(fill_color='black', back_color='white')
    if verbose: print(f"Saving to {name}")
    img.save(name)


def print_qr(args: Args, otp_url: str) -> None:
    qr = QRCode()
    qr.add_data(otp_url)
    qr.print_ascii()


def write_csv(args: Args, otps: Otps) -> None:
    if args.csv and len(otps) > 0:
        with open_file_or_stdout_for_csv(args.csv) as outfile:
            writer = csv.DictWriter(outfile, otps[0].keys())
            writer.writeheader()
            writer.writerows(otps)
        if not quiet: print(f"Exported {len(otps)} otp{'s'[:len(otps) != 1]} to csv {args.csv}")


def write_keepass_csv(args: Args, otps: Otps) -> None:
    if args.keepass and len(otps) > 0:
        has_totp = has_otp_type(otps, 'totp')
        has_hotp = has_otp_type(otps, 'hotp')
        if args.keepass != '-':
            otp_filename_totp = args.keepass if has_totp != has_hotp else add_pre_suffix(args.keepass, "totp")
            otp_filename_hotp = args.keepass if has_totp != has_hotp else add_pre_suffix(args.keepass, "hotp")
        else:
            otp_filename_totp = otp_filename_hotp = '-'
        if has_totp:
            count_totp_entries = write_keepass_totp_csv(otp_filename_totp, otps)
        if has_hotp:
            count_hotp_entries = write_keepass_htop_csv(otp_filename_hotp, otps)
        if not quiet:
            if count_totp_entries: print(f"Exported {count_totp_entries} totp entrie{'s'[:count_totp_entries != 1]} to keepass csv file {otp_filename_totp}")
            if count_hotp_entries: print(f"Exported {count_hotp_entries} hotp entrie{'s'[:count_hotp_entries != 1]} to keepass csv file {otp_filename_hotp}")


def write_keepass_totp_csv(otp_filename: str, otps: Otps) -> int:
    count_entries = 0
    with open_file_or_stdout_for_csv(otp_filename) as outfile:
        writer = csv.DictWriter(outfile, ["Title", "User Name", "TimeOtp-Secret-Base32", "Group"])
        writer.writeheader()
        for otp in otps:
            if otp['type'] == 'totp':
                writer.writerow({
                    'Title': otp['issuer'],
                    'User Name': otp['name'],
                    'TimeOtp-Secret-Base32': otp['secret'] if otp['type'] == 'totp' else None,
                    'Group': f"OTP/{otp['type'].upper()}"
                })
                count_entries += 1
    return count_entries


def write_keepass_htop_csv(otp_filename: str, otps: Otps) -> int:
    count_entries = 0
    with open_file_or_stdout_for_csv(otp_filename) as outfile:
        writer = csv.DictWriter(outfile, ["Title", "User Name", "HmacOtp-Secret-Base32", "HmacOtp-Counter", "Group"])
        writer.writeheader()
        for otp in otps:
            if otp['type'] == 'hotp':
                writer.writerow({
                    'Title': otp['issuer'],
                    'User Name': otp['name'],
                    'HmacOtp-Secret-Base32': otp['secret'] if otp['type'] == 'hotp' else None,
                    'HmacOtp-Counter': otp['counter'] if otp['type'] == 'hotp' else None,
                    'Group': f"OTP/{otp['type'].upper()}"
                })
                count_entries += 1
    return count_entries


def write_json(args: Args, otps: Otps) -> None:
    if args.json:
        with open_file_or_stdout(args.json) as outfile:
            json.dump(otps, outfile, indent=4)
        if not quiet: print(f"Exported {len(otps)} otp{'s'[:len(otps) != 1]} to json {args.json}")


def has_otp_type(otps: Otps, otp_type: str) -> bool:
    for otp in otps:
        if otp['type'] == otp_type:
            return True
    return False


def add_pre_suffix(file: str, pre_suffix: str) -> str:
    '''filename.ext, pre -> filename.pre.ext'''
    name, ext = os.path.splitext(file)
    return name + "." + pre_suffix + (ext if ext else "")


def open_file_or_stdout(filename: str) -> TextIO:
    '''stdout is denoted as "-".
    Note: Set before the following line:
    sys.stdout.close = lambda: None'''
    return open(filename, "w", encoding='utf-8') if filename != '-' else sys.stdout


def open_file_or_stdout_for_csv(filename: str) -> TextIO:
    '''stdout is denoted as "-".
    newline=''
    Note: Set before the following line:
    sys.stdout.close = lambda: None'''
    return open(filename, "w", encoding='utf-8', newline='') if filename != '-' else sys.stdout


def check_file_exists(filename: str) -> None:
    if filename != '-' and not os.path.isfile(filename):
        abort(f"Input file provided is non-existent or not a file."
              f"\ninput file: {filename}")


def is_binary(line: str) -> bool:
    try:
        line.startswith('#')
        return False
    except (UnicodeDecodeError, AttributeError, TypeError):
        return True


def next_qr_mode(qr_mode: QRMode) -> QRMode:
    return QRMode((qr_mode.value + 1) % len(QRMode))


def do_debug_checks() -> bool:
    log_debug('Do debug checks')
    log_debug('Try: import cv2')
    import cv2  # noqa: F401 # This is only a debug import
    log_debug('Try: import numpy as np')
    import numpy as np  # noqa: F401 # This is only a debug import
    print(color('\nDebug checks passed', colorama.Fore.GREEN))
    return True


# workaround for PYTHON <= 3.9 use: BaseException | None
def log_debug(*values: object, sep: Optional[str] = ' ') -> None:
    if colored:
        print(f"{colorama.Fore.CYAN}\nDEBUG: {str(values[0])}", *values[1:], colorama.Fore.RESET, sep)
    else:
        print(f"\nDEBUG: {str(values[0])}", *values[1:], sep)


# workaround for PYTHON <= 3.9 use: BaseException | None
def log_verbose(msg: str) -> None:
    print(color(msg, colorama.Fore.CYAN))


# workaround for PYTHON <= 3.9 use: BaseException | None
def log_warn(msg: str, exception: Optional[BaseException] = None) -> None:
    exception_text = "\nException: "
    eprint(color(f"\nWARN: {msg}{(exception_text + str(exception)) if exception else ''}", colorama.Fore.RED))


# workaround for PYTHON <= 3.9 use: BaseException | None
def log_error(msg: str, exception: Optional[BaseException] = None) -> None:
    exception_text = "\nException: "
    eprint(color(f"\nERROR: {msg}{(exception_text + str(exception)) if exception else ''}", colorama.Fore.RED))


def color(msg: str, color: Optional[str] = None) -> str:
    return f"{color if colored and color else ''}{msg}{colorama.Fore.RESET if colored and color else ''}"


def eprint(*values: object, **kwargs: Any) -> None:
    '''Print to stderr.'''
    print(*values, file=sys.stderr, **kwargs)


# workaround for PYTHON <= 3.9 use: BaseException | None
def abort(msg: str, exception: Optional[BaseException] = None) -> None:
    log_error(msg, exception)
    sys.exit(1)


if __name__ == '__main__':
    sys_main()
