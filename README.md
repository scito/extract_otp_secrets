# Extract TOTP/HOTP secret keys from Google Authenticator

[![CI Status](https://github.com/scito/extract_otp_secret_keys/actions/workflows/ci.yml/badge.svg)](https://github.com/scito/extract_otp_secret_keys/actions/workflows/ci.yml)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/protobuf)
[![GitHub Pipenv locked Python version](https://img.shields.io/github/pipenv/locked/python-version/scito/extract_otp_secret_keys)](https://github.com/scito/extract_otp_secret_keys/blob/master/Pipfile.lock)
![protobuf version](https://img.shields.io/badge/protobuf-4.21.12-informational)
[![License](https://img.shields.io/github/license/scito/extract_otp_secret_keys)](https://github.com/scito/extract_otp_secret_keys/blob/master/LICENSE)
[![GitHub tag (latest SemVer)](https://img.shields.io/github/v/tag/scito/extract_otp_secret_keys?sort=semver&label=version)](https://github.com/scito/extract_otp_secret_keys/tags)
[![Stand With Ukraine](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/badges/StandWithUkraine.svg)](https://stand-with-ukraine.pp.ua)

---

Extract two-factor authentication (2FA, TFA, OTP) secret keys from export QR codes of "Google Authenticator" app.
The secret and otp values can be printed and exported to json or csv. The QR codes can be printed or saved as PNG images.

## Installation

git clone https://github.com/scito/extract_otp_secret_keys.git
cd extract_otp_secret_keys

## Usage

1. Open "Google Authenticator" app on the mobile phone
2. Export the QR codes from "Google Authenticator" app
3. Read QR codes with a QR code reader (e.g. from another phone)
4. Save the captured QR codes in the QR code reader to a text file, e.g. example_export.txt. Save each QR code on a new line. (The captured QR codes look like `otpauth-migration://offline?data=...`)
5. Transfer the file to the computer where his script is installed.
6. Call this script with the file as input:

    python extract_otp_secret_keys.py example_export.txt

## Program help: arguments and options

<pre>usage: extract_otp_secret_keys.py [-h] [--json FILE] [--csv FILE] [--keepass FILE] [--printqr] [--saveqr DIR] [--verbose] [--quiet] infile

positional arguments:
  infile                   file or - for stdin (default: -) with "otpauth-migration://..." URLs separated by newlines, lines starting with # are ignored

options:
  -h, --help               show this help message and exit
  --json FILE, -j FILE     export json file
  --csv FILE, -c FILE      export csv file
  --keepass FILE, -k FILE  export totp/hotp csv file(s) for KeePass
  --printqr, -p            print QR code(s) as text to the terminal (requires qrcode module)
  --saveqr DIR, -s DIR     save QR code(s) as images to the given folder (requires qrcode module)
  --verbose, -v            verbose output
  --quiet, -q              no stdout output</pre>

## Dependencies

    pip install -r requirements.txt

Known to work with

* Python 3.10.8, protobuf 4.21.9, qrcode 7.3.1, and pillow 9.2
* Python 3.11.1, protobuf 4.21.12, qrcode 7.3.1, and pillow 9.2

For protobuf versions 3.14.0 or similar or Python 3.6, use the extract_otp_secret_keys version 1.4.0.

### Optional

For printing QR codes, the qrcode module is required, otherwise it can be omitted.

    pip install qrcode[pil]

## Features

* Free and open source
* Supports Google Authenticator export
* All functionality in one Python script: extract_otp_secret_keys.py (except protobuf generated code in protobuf_generated_python)
* Supports TOTP and HOTP
* Generates QR codes
* Various export formats:
    * CSV
    * JSON
    * Dedicated CSV for KeePass
    * QR code images
* Many ways to run the script:
    * Native Python
    * pipenv
    * venv
    * Docker
    * VSCode devcontainer
    * devbox
    * pip

## KeePass

[KeePass 2.51](https://keepass.info/news/n220506_2.51.html) (released in May 2022) and newer [support the generation of OTPs (TOTP and HOTP)](https://keepass.info/help/base/placeholders.html#otp).

KeePass can generate the second factor password (2FA) if the OTP secret is stored in `TimeOtp-Secret-Base32` string field for TOTP or `HmacOtp-Secret-Base32` string field for HOTP. You view or edit them in entry dialog on the 'Advanced' tab page.

KeePass provides menu commands in the main window for generating one-time passwords ('Copy HMAC-Based OTP', 'Show HMAC-Based OTP', 'Copy Time-Based OTP', 'Show Time-Based OTP'). Furthermore, one-time passwords can be generated during auto-type using the {HMACOTP} and {TIMEOTP} placeholders.

In order to simplify the usage of the second factor password generation in KeePass a specific KeePass CSV export is available with option `-keepass` or `-k`. This KeePass CSV file can be imported by the ["Generic CSV Importer" of KeePass](https://keepass.info/help/kb/imp_csv.html).

If TOTP and HOTP entries have to be exported, then two files with an intermediate suffix .totp or .hotp will be added to the KeePass export filename.

Example:
- Only TOTP entries to export and parameter --keepass example_keepass_output.csv<br>
    → example_keepass_output.csv with TOTP entries will be exported
- Only HOTP entries to export and parameter --keepass example_keepass_output.csv<br>
    → example_keepass_output.csv with HOTP entries will be exported
- If both TOTP and HOTP entries to export and parameter --keepass example_keepass_output.csv<br>
    → example_keepass_output.totp.csv with TOTP entries will be exported<br>
    → example_keepass_output.hotp.csv with HOTP entries will be exported

Import CSV with TOTP entries in KeePass as

- Title
- User Name
- String (TimeOtp-Secret-Base32)
- Group (/)

Import CSV with HOTP entries in KeePass as

- Title
- User Name
- String (HmacOtp-Secret-Base32)
- String (HmacOtp-Counter)
- Group (/)

KeePass can be used as a backup for one time passwords (second factor) from the mobile phone.

## Technical background

The export QR code of "Google Authenticator" contains the URL `otpauth-migration://offline?data=...`.
The data parameter is a base64 encoded proto3 message (Google Protocol Buffers).

Command for regeneration of Python code from proto3 message definition file (only necessary in case of changes of the proto3 message definition or new protobuf versions):

    protoc --python_out=protobuf_generated_python google_auth.proto

The generated protobuf Python code was generated by protoc 21.12 (https://github.com/protocolbuffers/protobuf/releases/tag/v21.12).

## References

* Proto3 documentation: https://developers.google.com/protocol-buffers/docs/pythontutorial
* Template code: https://github.com/beemdevelopment/Aegis/pull/406

## Glossary

* OTP = One-time password
* TOTP = Time-based one-time password
* HOTP = HMAC-based one-time password (using a counter)
* 2FA = Second factor authentication
* TFA = Two factor authentication
* QR code = Quick response code

## Alternative installation methods

### pip

```
pip install git+https://github.com/scito/extract_otp_secret_keys
python -m extract_otp_secret_keys
```

#### Example

```
wget https://raw.githubusercontent.com/scito/extract_otp_secret_keys/master/example_export.txt
python -m extract_otp_secret_keys example_export.txt
```

### pipenv

You can you use [Pipenv](https://github.com/pypa/pipenv) for running extract_otp_secret_keys.

```
pipenv --rm
pipenv install
pipenv shell
python extract_otp_secret_keys.py example_export.txt
```

### Visual Studio Code Remote - Containers / VSCode devcontainer

You can you use [VSCode devcontainer](https://code.visualstudio.com/docs/remote/containers-tutorial) for running extract_otp_secret_keys.

Requirement: Docker

1. Start VSCode
2. Open extract_otp_secret_keys.code-workspace
3. Open VSCode command palette (Ctrl-Shift-P)
4. Type command "Remote-Containers: Reopen in Container"
5. Open integrated bash terminal in VSCode
6. Execute: python extract_otp_secret_keys.py example_export.txt

### venv

Alternatively, you can use a python virtual env for the dependencies:

    python -m venv venv
    . venv/bin/activate
    pip install -r requirements-dev.txt
    pip install -r requirements.txt

The requirements\*.txt files contain all the dependencies (also the optional ones).
To leave the python virtual env just call `deactivate`.

### devbox

Install [devbox](https://github.com/jetpack-io/devbox), which is a wrapper for nix. Then enter the environment with Python and the packages installed with:

```
devbox shell
```

### Docker

Install [Docker](https://docs.docker.com/get-docker/).

Build and run the app within the container:

```bash
docker build . -t extract_otp
docker run --rm -v "$(pwd)":/files:ro extract_otp -p example_export.txt
```

## Tests

### PyTest

There are basic [pytest](https://pytest.org)s, see `test_extract_otp_secret_keys_pytest.py`.

Run tests:

```
pytest
```
or
```
python -m pytest
```

### unittest

There are basic [unittest](https://docs.python.org/3.10/library/unittest.html)s, see `test_extract_otp_secret_keys_unittest.py`.

Run tests:

```
python -m unittest
```

### VSCode Setup

Setup for running the tests in VSCode.

1. Open VSCode command palette (Ctrl-Shift-P)
2. Type command "Python: Configure Tests"
3. Choose unittest or pytest. (pytest is recommended, both are supported)
4. Set ". Root" directory

## Maintenance

### Upgrade pip Packages

```
pip install -U -r requirements.txt
```

## Related projects

* [ZBar](https://github.com/mchehab/zbar) is an open source software suite for reading bar codes from various sources, including webcams.
* [Aegis Authenticator](https://github.com/beemdevelopment/Aegis) is a free, secure and open source 2FA app for Android.
* [Android OTP Extractor](https://github.com/puddly/android-otp-extractor) can extract your tokens from popular Android OTP apps and export them in a standard format or just display them as QR codes for easy importing. [Requires a _rooted_ Android phone.]

***

# #StandWithUkraine 🇺🇦

I have Ukrainian relatives and friends.

#RussiaInvadedUkraine on 24 of February 2022, at 05:00 the armed forces of the Russian Federation attacked Ukraine. Please, stand with Ukraine, stay tuned for updates on Ukraine's official sources and channels in English and support Ukraine in its fight for freedom and democracy in Europe.
