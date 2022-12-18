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
import fileinput
import sys
import csv
import json
from urllib.parse import parse_qs, urlencode, urlparse, quote
from os import path, makedirs
from re import compile as rcompile
import protobuf_generated_python.google_auth_pb2


def sys_main():
    main(sys.argv[1:])


def main(sys_args):
    global verbose, quiet

    # allow to use sys.stdout with with (avoid closing)
    sys.stdout.close = lambda: None

    args = parse_args(sys_args)
    verbose = args.verbose if args.verbose else 0
    quiet = args.quiet

    otps = extract_otps(args)
    write_csv(args, otps)
    write_keepass_csv(args, otps)
    write_json(args, otps)


def parse_args(sys_args):
    formatter = lambda prog: argparse.HelpFormatter(prog,max_help_position=52)
    arg_parser = argparse.ArgumentParser(formatter_class=formatter)
    arg_parser.add_argument('infile', help='file or - for stdin (default: -) with "otpauth-migration://..." URLs separated by newlines, lines starting with # are ignored')
    arg_parser.add_argument('--json', '-j', help='export json file or - for stdout', metavar=('FILE'))
    arg_parser.add_argument('--csv', '-c', help='export csv file or - for stdout', metavar=('FILE'))
    arg_parser.add_argument('--keepass', '-k', help='export totp/hotp csv file(s) for KeePass, - for stdout', metavar=('FILE'))
    arg_parser.add_argument('--printqr', '-p', help='print QR code(s) as text to the terminal (requires qrcode module)', action='store_true')
    arg_parser.add_argument('--saveqr', '-s', help='save QR code(s) as images to the given folder (requires qrcode module)', metavar=('DIR'))
    arg_parser.add_argument('--verbose', '-v', help='verbose output', action='count')
    arg_parser.add_argument('--quiet', '-q', help='no stdout output', action='store_true')
    args = arg_parser.parse_args(sys_args)
    if args.verbose and args.quiet:
        eprint("The arguments --verbose and --quiet are mutually exclusive.")
        sys.exit(1)
    return args


def extract_otps(args):
    global verbose, quiet
    quiet = args.quiet

    otps = []

    i = j = 0
    finput = fileinput.input(args.infile)
    try:
        for line in (line.strip() for line in finput):
            if verbose: print(line)
            if line.startswith('#') or line == '': continue
            i += 1
            payload = get_payload_from_line(line, i, args)

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
    finally:
        finput.close()
    return otps


def get_payload_from_line(line, i, args):
    global verbose
    if not line.startswith('otpauth-migration://'):
        eprint('\nWARN: line is not a otpauth-migration:// URL\ninput file: {}\nline "{}"\nProbably a wrong file was given'.format(args.infile, line))
    parsed_url = urlparse(line)
    if verbose > 1: print('\nDEBUG: parsed_url={}'.format(parsed_url))
    try:
        params = parse_qs(parsed_url.query, strict_parsing=True)
    except: # Not necessary for Python >= 3.11
        params = []
    if verbose > 1: print('\nDEBUG: querystring params={}'.format(params))
    if 'data' not in params:
        eprint('\nERROR: no data query parameter in input URL\ninput file: {}\nline "{}"\nProbably a wrong file was given'.format(args.infile, line))
        sys.exit(1)
    data_base64 = params['data'][0]
    if verbose > 1: print('\nDEBUG: data_base64={}'.format(data_base64))
    data_base64_fixed = data_base64.replace(' ', '+')
    if verbose > 1: print('\nDEBUG: data_base64_fixed={}'.format(data_base64))
    data = base64.b64decode(data_base64_fixed, validate=True)
    payload = protobuf_generated_python.google_auth_pb2.MigrationPayload()
    try:
        payload.ParseFromString(data)
    except:
        eprint('\nERROR: Cannot decode otpauth-migration migration payload.')
        eprint('data={}'.format(data_base64))
        exit(1);
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
    otp_url = 'otpauth://{}/{}?'.format(get_otp_type_str_from_code(raw_otp.type), quote(raw_otp.name)) + urlencode(url_params)
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
    if not (path.exists(dir)): makedirs(dir, exist_ok=True)
    pattern = rcompile(r'[\W_]+')
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
            if count_totp_entries > 0: print("Exported {} totp entries to keepass csv file {}".format(count_totp_entries, otp_filename_totp))
            if count_hotp_entries > 0: print("Exported {} hotp entries to keepass csv file {}".format(count_hotp_entries, otp_filename_hotp))


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
    name, ext = path.splitext(file)
    return name + "." + pre_suffix + (ext if ext else "")


def open_file_or_stdout(filename):
    '''stdout is denoted as "-".
    Note: Set before the following line:
    sys.stdout.close = lambda: None'''
    return open(filename, "w") if filename != '-' else sys.stdout


def open_file_or_stdout_for_csv(filename):
    '''stdout is denoted as "-".
    newline=''
    Note: Set before the following line:
    sys.stdout.close = lambda: None'''
    return open(filename, "w", newline='') if filename != '-' else sys.stdout


def eprint(*args, **kwargs):
    '''Print to stderr.'''
    print(*args, file=sys.stderr, **kwargs)


if __name__ == '__main__':
    sys_main()
