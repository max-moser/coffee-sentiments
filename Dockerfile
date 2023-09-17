FROM python:3.11

WORKDIR /var/coffee
COPY . /var/coffee

RUN apt-get update && apt-get -y full-upgrade && apt-get install -y pipenv
RUN pipenv install

CMD ["./start.sh"]
