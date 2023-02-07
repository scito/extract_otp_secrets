#!/bin/sh

# Create a folder (named dmg) to prepare our DMG in (if it doesn't already exist).

# https://www.pythonguis.com/tutorials/packaging-pyqt5-applications-pyinstaller-macos-dmg/

mkdir -p dist/dmg
# Empty the dmg folder.
rm -r dist/dmg/*
# Copy the app bundle to the dmg folder.
cp -r "dist/extract_otp_secrets.app" dist/dmg
# If the DMG already exists, delete it.
test -f "dist/extract_otp_secrets.dmg" && rm "dist/extract_otp_secrets.dmg"
create-dmg \
  --volname "Extract OTP Secrets" \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon-size 100 \
  --hide-extension "extract_otp_secrets.app" \
  --app-drop-link 425 120 \
  "dist/extract_otp_secrets.dmg" \
  "dist/dmg/"
