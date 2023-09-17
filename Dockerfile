FROM python:3.11

WORKDIR /var/coffee
COPY . /var/coffee

RUN apt-get update && apt-get -y full-upgrade && apt-get install -y pipx
RUN pipx install pipenv && pipx run pipenv install

CMD ["./.start.sh"]
