import sys
from collections import defaultdict
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, List

from flask import Flask, jsonify, render_template, request


class VoteEnum(IntEnum):
    Downvote = 0
    Upvote = 1


@dataclass
class Vote:
    name: str
    vote: VoteEnum


app = Flask("coffee")
app.config.from_pyfile("coffee.cfg")
app.template_folder = "templates"
votes = defaultdict(list)


def _add_vote(coffee_variant: str, name: str, vote: VoteEnum) -> bool:
    for existing_vote in votes[coffee_variant]:
        if existing_vote.name.lower() == name.lower():
            return False

    votes[coffee_variant].append(Vote(name=name, vote=vote))
    return True


@app.template_filter()
def summarize_votes(vote_list: List[Vote]) -> str:
    upvotes = [v for v in vote_list if v.vote == VoteEnum.Upvote]
    downvotes = [v for v in vote_list if v.vote == VoteEnum.Downvote]

    return f"+{len(upvotes)} / -{len(downvotes)}"


@app.template_filter()
def display_vote(vote: VoteEnum) -> str:
    value = "unknown"
    if vote == VoteEnum.Upvote:
        value = "like"
    elif vote == VoteEnum.Downvote:
        value = "dislike"

    return value


@app.route("/")
def show_overview():
    return render_template("overview.jinja", votes=votes)


@app.route("/vote", methods=["POST"])
def vote():
    try:
        variant = request.values["variant"]
        vote = request.values["vote"]
        name = request.values["name"]

        if _add_vote(variant, name, VoteEnum(int(vote))):
            return jsonify({"message": "thanks for voting!"})
        else:
            return jsonify({"message": "no double votes!"}), 403

    except KeyError as e:
        return jsonify({"message": f"could not find the value for {e}"}), 400

    except Exception as e:
        print(e, file=sys.stderr)
        return jsonify({"message": e}), 400


def _add_test_data(app: Flask, votes: Dict[str, List[Vote]]) -> None:
    if app.config.get("TESTING", False):
        _add_vote("Corsini", "Max", VoteEnum.Upvote)
        _add_vote("Indiana", "Max", VoteEnum.Downvote)


_add_test_data(app, votes)
if __name__ == "__main__":
    app.run()
