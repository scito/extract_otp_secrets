import pathlib
from setuptools import setup

setup(
    name='extract_otp_secret_keys',
    version='1.6.0',
    description='Extract two-factor authentication (2FA, TFA, OTP) secret keys from export QR codes of "Google Authenticator" app',

    long_description=(pathlib.Path(__file__).parent / 'README.md').read_text(),
    long_description_content_type='text/markdown',

    url='https://github.com/scito/extract_otp_secret_keys',
    author='scito',
    author_email='info@scito.ch',

    classifiers=[
        'Development Status :: 5 - Production/Stable',

        'Environment :: Console',
        'Topic :: System :: Archiving :: Backup',
        'Topic :: Utilities',

        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',

        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',

        'Programming Language :: Python'
        'Natural Language :: English',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    ],

    keywords='python security json otp csv protobuf qrcode two-factor totp google-authenticator recovery proto3 mfa two-factor-authentication tfa qr-codes otpauth 2fa security-tools',

    py_modules=['extract_otp_secret_keys', 'protobuf_generated_python.google_auth_pb2'],
    entry_points={
        'console_scripts': [
            'extract_otp_secret_keys = extract_otp_secret_keys:sys_main',
        ]
    },

    python_requires='>=3.7, <4',
    install_requires=[
        'protobuf',
        'qrcode',
        'Pillow',
        'qreader',
        'opencv-python'
    ],

    project_urls={
        'Bug Reports': 'https://github.com/scito/extract_otp_secret_keys/issues',
        'Source': 'https://github.com/scito/extract_otp_secret_keys',
    },

    license='GNU General Public License v3 (GPLv3)',
)
