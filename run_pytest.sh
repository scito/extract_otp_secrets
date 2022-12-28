#!/bin/sh
cd /extract
pip install -U pytest pytest-mock && pip install --no-deps . && pytest "$@"
