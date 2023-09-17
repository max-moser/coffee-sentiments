#!/bin/bash
#
# script for running `start.sh` with the `pipx` path prefixed
# this is intended to fix `pipenv` not being found in the container
#

PATH="/root/.local/bin:${PATH}" bash ./start.sh
