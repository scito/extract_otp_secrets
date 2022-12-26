#!/bin/sh
cd /extract
pip install -U pytest && pytest "$@"
