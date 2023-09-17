#!/bin/bash
#
# start the application with gunicorn
#

certfile="ssl/ssl.crt"
keyfile="ssl/ssl.key"

if [[ ! -f "${keyfile}" ]]; then
    echo >&2 "warn: using test key!"
    keyfile="ssl/test.key"
fi

if [[ ! -f "${certfile}" ]]; then
    echo >&2 "warn: using test cert!"
    certfile="ssl/test.crt"
fi

pipenv run gunicorn --bind "0.0.0.0:5000" \
                    --keyfile "${keyfile}" \
                    --certfile "${certfile}" \
                    --access-logfile "/dev/stdout" \
                    "app:app"
