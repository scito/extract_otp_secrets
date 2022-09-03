# Extract two-factor authentication (2FA, TFA) secret keys from export QR codes of "Google Authenticator" app
#
# Usage:
# 1. Export the QR codes from "Google Authenticator" app
# 2. Read QR codes with QR code reader (e.g. with a second device)
# 3. Save the captured QR codes in a text file. Save each QR code on a new line. (The captured QR codes look like "otpauth-migration://offline?data=...")
# 4. Call this script with the file as input:
#    python extract_otp_secret_keys.py -p example_export.txt
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
from os import path, mkdir
from re import sub, compile as rcompile
import generated_python.google_auth_pb2

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--verbose', '-v', help='verbose output', action='store_true')
arg_parser.add_argument('--saveqr', '-s', help='save QR code(s) as images to the "qr" subfolder', action='store_true')
arg_parser.add_argument('--printqr', '-p', help='print QR code(s) as text to the terminal', action='store_true')
arg_parser.add_argument('--json', '-j', help='export to json file')
arg_parser.add_argument('--csv', '-c', help='export to csv file')
arg_parser.add_argument('infile', help='file or - for stdin (default: -) with "otpauth-migration://..." URLs separated by newlines, lines starting with # are ignored')
args = arg_parser.parse_args()

if args.saveqr or args.printqr: from qrcode import QRCode
verbose = args.verbose

# https://stackoverflow.com/questions/40226049/find-enums-listed-in-python-descriptor-for-protobuf
def get_enum_name_by_number(parent, field_name):
    field_value = getattr(parent, field_name)
    return parent.DESCRIPTOR.fields_by_name[field_name].enum_type.values_by_number.get(field_value).name

def convert_secret_from_bytes_to_base32_str(bytes):
    return str(base64.b32encode(bytes), 'utf-8').replace('=', '')

def save_qr(data, name):
    qr = QRCode()
    qr.add_data(data)
    img = qr.make_image(fill_color='black', back_color='white')
    if verbose: print('Saving to {}'.format(name))
    img.save(name)

def print_qr(data):
    qr = QRCode()
    qr.add_data(data)
    qr.print_ascii()

otps = []

i = j = 0
for line in (line.strip() for line in fileinput.input(args.infile)):
    if verbose: print(line)
    if line.startswith('#') or line == '': continue
    if not line.startswith('otpauth-migration://'): print('\nWARN: line is not a otpauth-migration:// URL\ninput file: {}\nline "{}"\nProbably a wrong file was given'.format(args.infile, line))
    parsed_url = urlparse(line)
    params = parse_qs(parsed_url.query)
    if not 'data' in params:
        print('\nERROR: no data query parameter in input URL\ninput file: {}\nline "{}"\nProbably a wrong file was given'.format(args.infile, line))
        sys.exit(1)
    data_encoded = params['data'][0]
    data = base64.b64decode(data_encoded)
    payload = generated_python.google_auth_pb2.MigrationPayload()
    payload.ParseFromString(data)
    i += 1
    if verbose: print('\n{}. Payload Line'.format(i), payload, sep='\n')

    # pylint: disable=no-member
    for otp in payload.otp_parameters:
        j += 1
        if verbose: print('\n{}. Secret Key'.format(j))
        else: print()
        print('Name:   {}'.format(otp.name))
        secret = convert_secret_from_bytes_to_base32_str(otp.secret)
        print('Secret: {}'.format(secret))
        if otp.issuer: print('Issuer: {}'.format(otp.issuer))
        otp_type = get_enum_name_by_number(otp, 'type')
        print('Type:   {}'.format(otp_type))
        url_params = { 'secret': secret }
        if otp.type == 1: url_params['counter'] = otp.counter
        if otp.issuer: url_params['issuer'] = otp.issuer
        otp_url = 'otpauth://{}/{}?'.format('totp' if otp.type == 2 else 'hotp', quote(otp.name)) + urlencode(url_params)
        if verbose: print(otp_url)
        if args.printqr:
            print_qr(otp_url)
        if args.saveqr:
            if not(path.exists('qr')): mkdir('qr')
            pattern = rcompile(r'[\W_]+')
            file_otp_name = pattern.sub('', otp.name)
            file_otp_issuer = pattern.sub('', otp.issuer)
            save_qr(otp_url, 'qr/{}-{}{}.png'.format(j, file_otp_name, '-' + file_otp_issuer if file_otp_issuer else ''))

        otps.append({
            "name": otp.name,
            "secret": secret,
            "issuer": otp.issuer,
            "type": otp_type,
            "url": otp_url
            })

if args.csv and len(otps) > 0:
    with open(args.csv, "w") as outfile:
        writer = csv.DictWriter(outfile, otps[0].keys())
        writer.writeheader()
        writer.writerows(otps)
    print("Exported {} otps to csv".format(len(otps)))

if args.json:
    with open(args.json, "w") as outfile:
        json.dump(otps, outfile, indent = 4)
    print("Exported {} otp entries to json".format(len(otps)))
