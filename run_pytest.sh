#!/bin/sh
cd /extract
mkdir -p tests
ln -sf /extract/data tests/data
pip install -U pytest pytest-mock && pytest "$@"
