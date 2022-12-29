# Extract two-factor authentication (2FA, TFA) secret keys from export QR codes of "Google Authenticator" app
#
# Usage:
# 1. Export the QR codes from "Google Authenticator" app
# 2. Read QR codes with QR code reader (e.g. with a second device)
# 3. Save the captured QR codes in a text file. Save each QR code on a new line. (The captured QR codes look like "otpauth-migration://offline?data=...")
# 4. Call this script with the file as input:
#    python extract_otp_secret_keys.py example_export.txt
#
# Requirement:
# The protobuf package of Google for proto3 is required for running this script.
# pip install protobuf
#
# Optional:
# For printing QR codes, the qrcode module is required
# pip install qrcode
#
# Technical background:
# The export QR code of "Google Authenticator" contains the URL "otpauth-migration://offline?data=...".
# The data parameter is a base64 encoded proto3 message (Google Protocol Buffers).
#
# Command for regeneration of Python code from proto3 message definition file (only necessary in case of changes of the proto3 message definition):
# protoc --python_out=generated_python google_auth.proto
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

import argparse
import base64
import csv
import fileinput
import json
import os
import re
import sys
import urllib.parse as urlparse
from enum import Enum
from operator import add

from qrcode import QRCode

import protobuf_generated_python.google_auth_pb2


try:
    import cv2
    import numpy

    try:
        import pyzbar.pyzbar as zbar
        from qreader import QReader
    except ImportError as e:
        raise SystemExit(f"""
ERROR: Cannot import QReader module. This problem is probably due to the missing zbar shared library.
On Linux and macOS libzbar0 must be installed.
See in README.md for the installation of the libzbar0.
Exception: {e}""")
    qreader_available = True
except ImportError as e:
    qreader_available = False


def sys_main():
    main(sys.argv[1:])


def main(sys_args):
    # allow to use sys.stdout with with (avoid closing)
    sys.stdout.close = lambda: None

    args = parse_args(sys_args)
    if verbose: print(f"QReader installed: {qreader_available}")

    otps = extract_otps(args)
    write_csv(args, otps)
    write_keepass_csv(args, otps)
    write_json(args, otps)


def parse_args(sys_args):
    global verbose, quiet
    formatter = lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=52)
    description_text = "Extracts one time password (OTP) secret keys from QR codes, e.g. from Google Authenticator app."
    if qreader_available:
        description_text += "\nIf no infiles are provided, the QR codes are interactively captured from the camera."
    example_text = """examples:
python extract_otp_secret_keys.py
python extract_otp_secret_keys.py example_*.txt
python extract_otp_secret_keys.py - < example_export.txt
python extract_otp_secret_keys.py --csv - example_*.png | tail -n+2
python extract_otp_secret_keys.py = < example_export.png"""

    arg_parser = argparse.ArgumentParser(formatter_class=formatter,
                                         description=description_text,
                                         epilog=example_text)
    arg_parser.add_argument('infile', help="""a) file or - for stdin with 'otpauth-migration://...' URLs separated by newlines, lines starting with # are ignored;
b) image file containing a QR code or = for stdin for an image containing a QR code""", nargs='*' if qreader_available else '+')
    if qreader_available:
        arg_parser.add_argument('--camera', '-C', help='camera number of system (default camera: 0)', default=0, nargs=1, metavar=('NUMBER'))
    arg_parser.add_argument('--json', '-j', help='export json file or - for stdout', metavar=('FILE'))
    arg_parser.add_argument('--csv', '-c', help='export csv file or - for stdout', metavar=('FILE'))
    arg_parser.add_argument('--keepass', '-k', help='export totp/hotp csv file(s) for KeePass, - for stdout', metavar=('FILE'))
    arg_parser.add_argument('--printqr', '-p', help='print QR code(s) as text to the terminal (requires qrcode module)', action='store_true')
    arg_parser.add_argument('--saveqr', '-s', help='save QR code(s) as images to the given folder (requires qrcode module)', metavar=('DIR'))
    output_group = arg_parser.add_mutually_exclusive_group()
    output_group.add_argument('--verbose', '-v', help='verbose output', action='count')
    output_group.add_argument('--quiet', '-q', help='no stdout output, except output set by -', action='store_true')
    args = arg_parser.parse_args(sys_args)
    if args.csv == '-' or args.json == '-' or args.keepass == '-':
        args.quiet = args.q = True

    verbose = args.verbose if args.verbose else 0
    quiet = True if args.quiet else False

    return args


def extract_otps(args):
    if not args.infile:
        return extract_otps_from_camera(args)
    else:
        return extract_otps_from_files(args)


def extract_otps_from_camera(args):
    if verbose: print("Capture QR codes from camera")
    otp_urls = []
    otps = []

    QRMode = Enum('QRMode', ['QREADER', 'DEEP_QREADER', 'CV2'], start = 0)
    qr_mode = QRMode.QREADER
    if verbose: print(f"QR reading mode: {qr_mode}")

    cam = cv2.VideoCapture(args.camera)
    window_name = "Extract OTP Secret Keys: Capture QR Codes from Camera"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    neutral_color = 255, 0, 255
    sucess_color = 0, 255, 0
    font = cv2.FONT_HERSHEY_PLAIN
    font_scale = 1
    font_thickness = 1
    pos_text = 5, 20
    font_dy = 0, cv2.getTextSize("M", font, font_scale, font_thickness)[0][1] + 5
    font_line = cv2.LINE_AA
    rect_thickness = 5

    decoder = QReader()
    while True:
        success, img = cam.read()
        if not success:
            eprint("ERROR: Failed to capture image")
            break
        if qr_mode in [QRMode.QREADER, QRMode.DEEP_QREADER]:
            bbox, found = decoder.detect(img)
            if qr_mode == QRMode.DEEP_QREADER:
                otp_url = decoder.detect_and_decode(img)
            elif qr_mode == QRMode.QREADER:
                otp_url = decoder.decode(img, bbox) if found else None
            if found:
                cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), sucess_color if otp_url else neutral_color, rect_thickness)
            if otp_url:
                extract_otps_from_otp_url(otp_url, otp_urls, otps, args)
        elif qr_mode == QRMode.CV2:
            for qrcode in zbar.decode(img):
                otp_url = qrcode.data.decode('utf-8')
                pts = numpy.array([qrcode.polygon], numpy.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(img, [pts], True, sucess_color if otp_url else neutral_color, rect_thickness)
                extract_otps_from_otp_url(otp_url, otp_urls, otps, args)
        else:
            assert False, f"ERROR: Wrong QReader mode {qr_mode.name}"

        cv2.putText(img, f"Mode: {qr_mode.name} (Hit space to change)", pos_text, font, font_scale, neutral_color, font_thickness, font_line)
        cv2.putText(img, "Hit ESC to quit", tuple(map(add, pos_text, font_dy)), font, font_scale, neutral_color, font_thickness, font_line)

        window_dim = cv2.getWindowImageRect(window_name)
        qrcodes_text = f"{len(otp_urls)} QR code{'s'[:len(otp_urls) != 1]} captured"
        pos_qrcodes_text = window_dim[2] - cv2.getTextSize(qrcodes_text, font, font_scale, font_thickness)[0][0] - 5, pos_text[1]
        cv2.putText(img, qrcodes_text, pos_qrcodes_text, font, font_scale, neutral_color, font_thickness, font_line)

        otps_text = f"{len(otps)} otp{'s'[:len(otps) != 1]} extracted"
        pos_otps_text = window_dim[2] - cv2.getTextSize(otps_text, font, font_scale, font_thickness)[0][0] - 5, pos_text[1] + font_dy[1]
        cv2.putText(img, otps_text, pos_otps_text, font, font_scale, neutral_color, font_thickness, font_line)
        cv2.imshow(window_name, img)

        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord('q') or key == 13:
            # ESC pressed
            break
        elif key == 32:
            qr_mode = QRMode((qr_mode.value + 1) % len(QRMode))
            if verbose: print(f"QR reading mode: {qr_mode}")

    cam.release()
    cv2.destroyAllWindows()

    return otps


def extract_otps_from_otp_url(otp_url, otp_urls, otps, args):
    if otp_url and verbose: print(otp_url)
    if otp_url and otp_url not in otp_urls:
        otp_urls.append(otp_url)
        extract_otp_from_otp_url(otp_url, otps, len(otp_urls), len(otps), 'camera', args)
        if verbose: print(f"{len(otps)} otp{'s'[:len(otps) != 1]} from {len(otp_urls)} QR code{'s'[:len(otp_urls) != 1]} extracted")


def extract_otps_from_files(args):
    otps = []

    i = j = k = 0
    if verbose: print(f"Input files: {args.infile}")
    for infile in args.infile:
        if verbose: print(f"Processing infile {infile}")
        k += 1
        for line in get_otp_urls_from_file(infile):
            if verbose: print(line)
            if line.startswith('#') or line == '': continue
            i += 1
            j = extract_otp_from_otp_url(line, otps, i, j, infile, args)
    if verbose: print(f"{k} infile{'s'[:k != 1]} processed")
    return otps


def get_otp_urls_from_file(filename):
    # stdin stream cannot be rewinded, thus distinguish, use - for utf-8 stdin and = for binary image stdin
    if filename != '=':
        check_file_exists(filename)
        lines = read_lines_from_text_file(filename)
        if lines or filename == '-':
            return lines

    # could not process text file, try reading as image
    if filename != '-' and qreader_available:
        return convert_img_to_otp_url(filename)

    return []


def read_lines_from_text_file(filename):
    if verbose: print(f"Reading lines of {filename}")
    finput = fileinput.input(filename)
    try:
        lines = []
        for line in (line.strip() for line in finput):
            if verbose: print(line)
            if is_binary(line):
                abort("\nBinary input was given in stdin, please use = instead of - as infile argument for images.")
            # unfortunately yield line leads to random test fails
            lines.append(line)
        if not lines:
            eprint(f"WARN: {filename.replace('-', 'stdin')} is empty")
        return lines
    except UnicodeDecodeError:
        if filename == '-':
            abort("\nERROR: Unable to open text file form stdin. "
            "In case you want read an image file from stdin, you must use '=' instead of '-'.")
        else: # The file is probably an image, process below
            return None
    finally:
        finput.close()


def extract_otp_from_otp_url(otpauth_migration_url, otps, i, j, infile, args):
    payload = get_payload_from_otp_url(otpauth_migration_url, i, infile)

    # pylint: disable=no-member
    for raw_otp in payload.otp_parameters:
        j += 1
        if verbose: print(f"\n{j}. Secret Key")
        secret = convert_secret_from_bytes_to_base32_str(raw_otp.secret)
        otp_type_enum = get_enum_name_by_number(raw_otp, 'type')
        otp_type = get_otp_type_str_from_code(raw_otp.type)
        otp_url = build_otp_url(secret, raw_otp)
        otp = {
            "name": raw_otp.name,
            "secret": secret,
            "issuer": raw_otp.issuer,
            "type": otp_type,
            "counter": raw_otp.counter if raw_otp.type == 1 else None,
            "url": otp_url
        }
        otps.append(otp)
        if not quiet:
            print_otp(otp)
        if args.printqr:
            print_qr(args, otp_url)
        if args.saveqr:
            save_qr(otp, args, j)
        if not quiet:
            print()

    return j


def convert_img_to_otp_url(filename):
    if verbose: print(f"Reading image {filename}")
    try:
        if filename != '=':
            img = cv2.imread(filename)
        else:
            try:
                stdin = sys.stdin.buffer.read()
            except AttributeError:
                # Workaround for pytest, since pytest cannot monkeypatch sys.stdin.buffer
                stdin = sys.stdin.read()
            if not stdin:
                eprint("WARN: stdin is empty")
            try:
                img_array = numpy.frombuffer(stdin, dtype='uint8')
            except TypeError as e:
                abort(f"\nERROR: Cannot read binary stdin buffer. Exception: {e}")
            if not img_array.size:
                return []
            img = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)

        if img is None:
            abort(f"\nERROR: Unable to open file for reading.\ninput file: {filename}")

        decoded_text = QReader().detect_and_decode(img)
        if decoded_text is None:
            abort(f"\nERROR: Unable to read QR Code from file.\ninput file: {filename}")

        return [decoded_text]
    except Exception as e:
        abort(f"\nERROR: Encountered exception '{e}'.\ninput file: {filename}")


def get_payload_from_otp_url(otpauth_migration_url, i, input_source):
    if not otpauth_migration_url.startswith('otpauth-migration://'):
        eprint(f"\nWARN: line is not a otpauth-migration:// URL\ninput: {input_source}\nline '{otpauth_migration_url}'\nProbably a wrong file was given")
    parsed_url = urlparse.urlparse(otpauth_migration_url)
    if verbose > 2: print(f"\nDEBUG: parsed_url={parsed_url}")
    try:
        params = urlparse.parse_qs(parsed_url.query, strict_parsing=True)
    except:  # Not necessary for Python >= 3.11
        params = []
    if verbose > 2: print(f"\nDEBUG: querystring params={params}")
    if 'data' not in params:
        abort(f"\nERROR: no data query parameter in input URL\ninput file: {input_source}\nline '{otpauth_migration_url}'\nProbably a wrong file was given")
    data_base64 = params['data'][0]
    if verbose > 2: print(f"\nDEBUG: data_base64={data_base64}")
    data_base64_fixed = data_base64.replace(' ', '+')
    if verbose > 2: print(f"\nDEBUG: data_base64_fixed={data_base64_fixed}")
    data = base64.b64decode(data_base64_fixed, validate=True)
    payload = protobuf_generated_python.google_auth_pb2.MigrationPayload()
    try:
        payload.ParseFromString(data)
    except:
        abort(f"\nERROR: Cannot decode otpauth-migration migration payload.\n"
        f"data={data_base64}")
    if verbose:
        print(f"\n{i}. Payload Line", payload, sep='\n')

    return payload


# https://stackoverflow.com/questions/40226049/find-enums-listed-in-python-descriptor-for-protobuf
def get_enum_name_by_number(parent, field_name):
    field_value = getattr(parent, field_name)
    return parent.DESCRIPTOR.fields_by_name[field_name].enum_type.values_by_number.get(field_value).name


def get_otp_type_str_from_code(otp_type):
    return 'totp' if otp_type == 2 else 'hotp'


def convert_secret_from_bytes_to_base32_str(bytes):
    return str(base64.b32encode(bytes), 'utf-8').replace('=', '')


def build_otp_url(secret, raw_otp):
    url_params = {'secret': secret}
    if raw_otp.type == 1: url_params['counter'] = raw_otp.counter
    if raw_otp.issuer: url_params['issuer'] = raw_otp.issuer
    otp_url = f"otpauth://{get_otp_type_str_from_code(raw_otp.type)}/{urlparse.quote(raw_otp.name)}?" + urlparse.urlencode(url_params)
    return otp_url


def print_otp(otp):
    print(f"Name:    {otp['name']}")
    print(f"Secret:  {otp['secret']}")
    if otp['issuer']: print(f"Issuer:  {otp['issuer']}")
    print(f"Type:    {otp['type']}")
    if otp['type'] == 'hotp':
        print(f"Counter: {otp['counter']}")
    if verbose:
        print(otp['url'])


def save_qr(otp, args, j):
    dir = args.saveqr
    if not (os.path.exists(dir)): os.makedirs(dir, exist_ok=True)
    pattern = re.compile(r'[\W_]+')
    file_otp_name = pattern.sub('', otp['name'])
    file_otp_issuer = pattern.sub('', otp['issuer'])
    save_qr_file(args, otp['url'], f"{dir}/{j}-{file_otp_name}{'-' + file_otp_issuer if file_otp_issuer else ''}.png")
    return file_otp_issuer


def save_qr_file(args, data, name):
    qr = QRCode()
    qr.add_data(data)
    img = qr.make_image(fill_color='black', back_color='white')
    if verbose: print(f"Saving to {name}")
    img.save(name)


def print_qr(args, data):
    qr = QRCode()
    qr.add_data(data)
    qr.print_ascii()


def write_csv(args, otps):
    if args.csv and len(otps) > 0:
        with open_file_or_stdout_for_csv(args.csv) as outfile:
            writer = csv.DictWriter(outfile, otps[0].keys())
            writer.writeheader()
            writer.writerows(otps)
        if not quiet: print(f"Exported {len(otps)} otp{'s'[:len(otps) != 1]} to csv {args.csv}")


def write_keepass_csv(args, otps):
    if args.keepass and len(otps) > 0:
        has_totp = has_otp_type(otps, 'totp')
        has_hotp = has_otp_type(otps, 'hotp')
        otp_filename_totp = args.keepass if has_totp != has_hotp else add_pre_suffix(args.keepass, "totp")
        otp_filename_hotp = args.keepass if has_totp != has_hotp else add_pre_suffix(args.keepass, "hotp")
        count_totp_entries = 0
        count_hotp_entries = 0
        if has_totp:
            with open_file_or_stdout_for_csv(otp_filename_totp) as outfile:
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
                        count_totp_entries += 1
        if has_hotp:
            with open_file_or_stdout_for_csv(otp_filename_hotp) as outfile:
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
                        count_hotp_entries += 1
        if not quiet:
            if count_totp_entries > 0: print(f"Exported {count_totp_entries} totp entrie{'s'[:count_totp_entries != 1]} to keepass csv file {otp_filename_totp}")
            if count_hotp_entries > 0: print(f"Exported {count_hotp_entries} hotp entrie{'s'[:count_hotp_entries != 1]} to keepass csv file {otp_filename_hotp}")


def write_json(args, otps):
    if args.json:
        with open_file_or_stdout(args.json) as outfile:
            json.dump(otps, outfile, indent=4)
        if not quiet: print(f"Exported {len(otps)} otp{'s'[:len(otps) != 1]} to json {args.json}")


def has_otp_type(otps, otp_type):
    for otp in otps:
        if otp['type'] == otp_type:
            return True
    return False


def add_pre_suffix(file, pre_suffix):
    '''filename.ext, pre -> filename.pre.ext'''
    name, ext = os.path.splitext(file)
    return name + "." + pre_suffix + (ext if ext else "")


def open_file_or_stdout(filename):
    '''stdout is denoted as "-".
    Note: Set before the following line:
    sys.stdout.close = lambda: None'''
    return open(filename, "w", encoding='utf-8') if filename != '-' else sys.stdout


def open_file_or_stdout_for_csv(filename):
    '''stdout is denoted as "-".
    newline=''
    Note: Set before the following line:
    sys.stdout.close = lambda: None'''
    return open(filename, "w", encoding='utf-8', newline='') if filename != '-' else sys.stdout


def check_file_exists(filename):
    if filename != '-' and not os.path.isfile(filename):
        abort(f"\nERROR: Input file provided is non-existent or not a file."
        f"\ninput file: {filename}")


def is_binary(line):
    try:
        line.startswith('#')
        return False
    except (UnicodeDecodeError, AttributeError, TypeError):
        return True


def eprint(*args, **kwargs):
    '''Print to stderr.'''
    print(*args, file=sys.stderr, **kwargs)


def abort(*args, **kwargs):
    eprint(*args, **kwargs)
    sys.exit(1)


if __name__ == '__main__':
    sys_main()
