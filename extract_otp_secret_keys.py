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
import importlib
import json
import os
import re
import sys
import urllib.parse as urlparse

import protobuf_generated_python.google_auth_pb2

# These dynamic import are below:
# import cv2
# import numpy
# from qreader import QReader

def sys_main():
    main(sys.argv[1:])


def main(sys_args):
    global verbose, quiet, qreader_available

    # allow to use sys.stdout with with (avoid closing)
    sys.stdout.close = lambda: None
    # sys.stdout.reconfigure(encoding='utf-8')


    args = parse_args(sys_args)
    verbose = args.verbose if args.verbose else 0
    quiet = args.quiet

    otps = extract_otps(args)
    write_csv(args, otps)
    write_keepass_csv(args, otps)
    write_json(args, otps)


def parse_args(sys_args):
    formatter = lambda prog: argparse.RawDescriptionHelpFormatter(prog, max_help_position=52)
    example_text = '''examples:
python extract_otp_secret_keys.py example_*.txt
python extract_otp_secret_keys.py - < example_export.txt
python extract_otp_secret_keys.py --csv - example_*.png | tail -n+2
python extract_otp_secret_keys.py = < example_export.png'''

    arg_parser = argparse.ArgumentParser(formatter_class=formatter,
                                         epilog=example_text)
    arg_parser.add_argument('infile', help='1) file or - for stdin with "otpauth-migration://..." URLs separated by newlines, lines starting with # are ignored; or 2) image file containing a QR code or = for stdin for an image containing a QR code', nargs='+')
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
    return args


def extract_otps(args):
    global verbose, quiet
    quiet = args.quiet

    otps = []

    i = j = k = 0
    if verbose: print('Input files: {}'.format(args.infile))
    for infile in args.infile:
        if verbose: print('Processing infile {}'.format(infile))
        k += 1
        for line in get_lines_from_file(infile):
            if verbose: print(line)
            if line.startswith('#') or line == '': continue
            i += 1
            payload = get_payload_from_line(line, i, infile)

            # pylint: disable=no-member
            for raw_otp in payload.otp_parameters:
                j += 1
                if verbose: print('\n{}. Secret Key'.format(j))
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
                if not quiet:
                    print_otp(otp)
                if args.printqr:
                    print_qr(args, otp_url)
                if args.saveqr:
                    save_qr(otp, args, j)
                if not quiet:
                    print()

                otps.append(otp)
    if verbose: print('{} infile(s) processed'.format(k))
    return otps


def get_lines_from_file(filename):
    global qreader_available
    # stdin stream cannot be rewinded, thus distinguish, use - for utf-8 stdin and = for binary image stdin
    if filename != '=':
        check_file_exists(filename)
        lines = read_lines_from_text_file(filename)
        if lines or filename == '-':
            return lines

    # could not process text file, try reading as image
    if filename != '-':
        return convert_img_to_line(filename)


def read_lines_from_text_file(filename):
    if verbose: print('Reading lines of {}'.format(filename))
    finput = fileinput.input(filename)
    try:
        lines = []
        for line in (line.strip() for line in finput):
            if verbose: print(line)
            if is_binary(line):
                abort('\nBinary input was given in stdin, please use = instead of - as infile argument for images.')
            # unfortunately yield line leads to random test fails
            lines.append(line)
        if not lines:
            eprint("WARN: {} is empty".format(filename.replace('-', 'stdin')))
        return lines
    except UnicodeDecodeError:
        if filename == '-':
            abort('\nERROR: Unable to open text file form stdin. '
            'In case you want read an image file from stdin, you must use "=" instead of "-".')
        else: # The file is probably an image, process below
            return None
    finally:
        finput.close()


def convert_img_to_line(filename):
    try:
        import cv2
        import numpy
    except Exception as e:
        eprint("WARNING: No cv2 or numpy module installed. Exception: {}".format(str(e)))
        return []
    if verbose: print('Reading image {}'.format(filename))
    try:
        if filename != '=':
            image = cv2.imread(filename)
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
                abort('\nERROR: Cannot read binary stdin buffer. Exception: {}'.format(str(e)))
            if not img_array.size:
                return []
            image = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)

        if image is None:
            abort('\nERROR: Unable to open file for reading.\ninput file: {}'.format(filename))

        # dynamic import of QReader since this module has a dependency to zbar lib and import it only when necessary
        try:
            from qreader import QReader
        except ImportError as e:
            abort('''
ERROR: Cannot import QReader module. This problem is probably due to the missing zbar shared library.
On Linux and macOS libzbar0 must be installed.
See in README.md for the installation of the libzbar0.
Exception: {}'''.format(str(e)))

        decoder = QReader()
        decoded_text = decoder.detect_and_decode(image=image)
        if decoded_text is None:
            abort('\nERROR: Unable to read QR Code from file.\ninput file: {}'.format(filename))

        return [decoded_text]
    except Exception as e:
        abort('\nERROR: Encountered exception "{}".\ninput file: {}'.format(str(e), filename))


def get_payload_from_line(line, i, infile):
    global verbose
    if not line.startswith('otpauth-migration://'):
        eprint( '\nWARN: line is not a otpauth-migration:// URL\ninput file: {}\nline "{}"\nProbably a wrong file was given'.format(infile, line))
    parsed_url = urlparse.urlparse(line)
    if verbose > 1: print('\nDEBUG: parsed_url={}'.format(parsed_url))
    try:
        params = urlparse.parse_qs(parsed_url.query, strict_parsing=True)
    except:  # Not necessary for Python >= 3.11
        params = []
    if verbose > 1: print('\nDEBUG: querystring params={}'.format(params))
    if 'data' not in params:
        abort('\nERROR: no data query parameter in input URL\ninput file: {}\nline "{}"\nProbably a wrong file was given'.format(infile, line))
    data_base64 = params['data'][0]
    if verbose > 1: print('\nDEBUG: data_base64={}'.format(data_base64))
    data_base64_fixed = data_base64.replace(' ', '+')
    if verbose > 1: print('\nDEBUG: data_base64_fixed={}'.format(data_base64))
    data = base64.b64decode(data_base64_fixed, validate=True)
    payload = protobuf_generated_python.google_auth_pb2.MigrationPayload()
    try:
        payload.ParseFromString(data)
    except:
        abort('\nERROR: Cannot decode otpauth-migration migration payload.\n'
        'data={}'.format(data_base64))
    if verbose:
        print('\n{}. Payload Line'.format(i), payload, sep='\n')

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
    otp_url = 'otpauth://{}/{}?'.format(get_otp_type_str_from_code(raw_otp.type), urlparse.quote(raw_otp.name)) + urlparse.urlencode( url_params)
    return otp_url


def print_otp(otp):
    print('Name:    {}'.format(otp['name']))
    print('Secret:  {}'.format(otp['secret']))
    if otp['issuer']: print('Issuer:  {}'.format(otp['issuer']))
    print('Type:    {}'.format(otp['type']))
    if otp['type'] == 'hotp':
        print('Counter: {}'.format(otp['counter']))
    if verbose:
        print(otp['url'])


def save_qr(otp, args, j):
    dir = args.saveqr
    if not (os.path.exists(dir)): os.makedirs(dir, exist_ok=True)
    pattern = re.compile(r'[\W_]+')
    file_otp_name = pattern.sub('', otp['name'])
    file_otp_issuer = pattern.sub('', otp['issuer'])
    save_qr_file(args, otp['url'], '{}/{}-{}{}.png'.format(dir, j, file_otp_name, '-' + file_otp_issuer if file_otp_issuer else ''))
    return file_otp_issuer


def save_qr_file(args, data, name):
    from qrcode import QRCode
    global verbose
    qr = QRCode()
    qr.add_data(data)
    img = qr.make_image(fill_color='black', back_color='white')
    if verbose: print('Saving to {}'.format(name))
    img.save(name)


def print_qr(args, data):
    from qrcode import QRCode
    qr = QRCode()
    qr.add_data(data)
    qr.print_ascii()


def write_csv(args, otps):
    global verbose, quiet
    if args.csv and len(otps) > 0:
        with open_file_or_stdout_for_csv(args.csv) as outfile:
            writer = csv.DictWriter(outfile, otps[0].keys())
            writer.writeheader()
            writer.writerows(otps)
        if not quiet: print("Exported {} otps to csv {}".format(len(otps), args.csv))


def write_keepass_csv(args, otps):
    global verbose, quiet
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
                            'Group': "OTP/{}".format(otp['type'].upper())
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
                            'Group': "OTP/{}".format(otp['type'].upper())
                        })
                        count_hotp_entries += 1
        if not quiet:
            if count_totp_entries > 0: print( "Exported {} totp entries to keepass csv file {}".format(count_totp_entries, otp_filename_totp))
            if count_hotp_entries > 0: print( "Exported {} hotp entries to keepass csv file {}".format(count_hotp_entries, otp_filename_hotp))


def write_json(args, otps):
    global verbose, quiet
    if args.json:
        with open_file_or_stdout(args.json) as outfile:
            json.dump(otps, outfile, indent=4)
        if not quiet: print("Exported {} otp entries to json {}".format(len(otps), args.json))


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
        abort('\nERROR: Input file provided is non-existent or not a file.'
        '\ninput file: {}'.format(filename))


def is_binary(line):
    try:
        line.startswith('#')
        return False
    except (UnicodeDecodeError, AttributeError, TypeError):
        return True


def check_module_available(module_name):
    module_spec = importlib.util.find_spec(module_name)
    return module_spec is not None


def eprint(*args, **kwargs):
    '''Print to stderr.'''
    print(*args, file=sys.stderr, **kwargs)


def abort(*args, **kwargs):
    eprint(*args, **kwargs)
    sys.exit(1)


if __name__ == '__main__':
    sys_main()
