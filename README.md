# Coffee sentiments

Finally find the coffee variant that everybody in the office enjoys!

**Note**: This project is not intended to be run outside of safe environments!


## Requirements

* `python` 3.11
* `pipenv`


## Running

To run the web application locally, you need to install the dependencies via `pipenv install` first.  
Afterwards, you can start the application with `gunicorn` by running `./start.sh`.
The server will start listening to port `5000`.

A containerized setup is also available through `docker compose up`.  
The service will be available on port `443`.


## Usage

### Web UI

A simple web UI is available on the default path.


### API

#### `POST /api/vote`

Give a personal rating for one of the available coffee variants.

This endpoint requires the following values to be set:
* `variant` (string): The coffee variant you're voting for.
* `name` (string): Your name. There can only be a single vote given per name.
* `vote` (integer): Your vote. `0` is a dislike, `1` is a like.

Example use with `HTTPie`:
```bash
https --verify=no --form https://localhost/api/vote name=Max variant=Corsini vote=1
```


#### `POST /api/variants`

Create a new coffee variant in the system.

The endpoint requires the following values to be set:
* `name` (string): The name for the new coffee variant.
* `token` (string): The admin token for authorization.

Example use with `HTTPie`:
```bash
https --verify=no --form https://localhost/api/variants name=Corsini token=e903828a-84f8-4d30-a0c5-e7fd942ecd78
```

**Note**:
The expected for the *admin token* value in the backend can be set through the `ADMIN_TOKEN` config item.
If set during startup, it will be read from the `COFFEE_ADMIN_TOKEN` environment variable.  
If no explicit value is set, a randomized token will be created during startup and printed to `stdout`.


#### `GET /api/export`

Exports all votes in a simple JSON format.
Example export:
```json
{
    "Corsini": {
        "Max": "+",
        "Tomasz": "-"
    },
    "BadCoffee": {
        "Max": "-"
    }
}
```
