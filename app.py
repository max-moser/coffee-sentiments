from enum import IntEnum
from typing import Dict, List, Tuple
from uuid import uuid4

from flask import Flask, current_app, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, NoResultFound

app = Flask("coffee")
app.config.from_pyfile("coffee.cfg")
app.template_folder = "templates"
sa = SQLAlchemy(app)

if "ADMIN_TOKEN" not in app.config:
    token = str(uuid4())
    print(f"admin token: {token}")
    app.config["ADMIN_TOKEN"] = token


class VoteEnum(IntEnum):
    Downvote = 0
    Upvote = 1


class CoffeeVariant(sa.Model):
    __tablename__ = "coffee_variants"

    id: sa.Mapped[int] = sa.mapped_column(primary_key=True)
    name: sa.Mapped[str] = sa.mapped_column(sa.String(), unique=True)
    votes: sa.Mapped[List["Vote"]] = sa.relationship(back_populates="variant")


class Vote(sa.Model):
    __tablename__ = "votes"

    id: sa.Mapped[int] = sa.mapped_column(primary_key=True)
    variant_id: sa.Mapped[int] = sa.mapped_column(sa.ForeignKey("coffee_variants.id"))
    variant: sa.Mapped[CoffeeVariant] = sa.relationship(back_populates="votes")
    name: sa.Mapped[str] = sa.mapped_column(sa.String())
    vote: sa.Mapped[VoteEnum] = sa.mapped_column(sa.Integer)


def _get_votes() -> Dict[str, List[Vote]]:
    votes = sa.session.execute(sa.select(Vote)).scalars()
    variants = sa.session.execute(sa.select(CoffeeVariant)).scalars()
    votes_dict = {v.name: [] for v in variants}
    for vote in votes:
        votes_dict[vote.variant.name].append(vote)

    return votes_dict


def _add_vote(coffee_variant: str, name: str, vote: VoteEnum) -> Tuple[bool, str]:
    try:
        votes = _get_votes()
        for existing_vote in votes[coffee_variant]:
            if existing_vote.name.lower() == name.lower():
                sa.session.rollback()
                return False, "no double votes!"

        variant = sa.session.execute(
            sa.select(CoffeeVariant).filter(CoffeeVariant.name == coffee_variant)
        ).scalar_one()
        v = Vote(variant=variant, name=name, vote=vote)
        sa.session.add(v)
        sa.session.commit()
        return True, "thanks for voting!"

    except NoResultFound:
        return False, "coffee variant not found!"

    except Exception as e:
        current_app.logger.error(e)
        return False, "unexpected error"


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
    votes = _get_votes()
    return render_template("overview.jinja", votes=votes)


@app.route("/export")
def export():
    votes = {
        variant: {
            vote.name: "+" if vote.vote == VoteEnum.Upvote else "-" for vote in votes
        }
        for variant, votes in _get_votes().items()
    }
    return jsonify(votes)


@app.route("/variants", methods=["POST"])
def add_coffee_variant():
    try:
        values = request.values.to_dict()
        token = request.values.get("token", None)
        if token is None:
            return jsonify({"message": "token required!"}), 401

        elif token != current_app.config["ADMIN_TOKEN"]:
            return jsonify({"message": "unrecognized token!"}), 403

        name = values["name"]
        variant = CoffeeVariant(name=name)
        sa.session.add(variant)
        sa.session.commit()

        return jsonify({"message": "added variant!"})

    except KeyError as e:
        app.logger.error(e)
        return jsonify({"message": f"missing the required value for {e}"}), 400

    except IntegrityError as e:
        app.logger.error(e)
        return jsonify({"message": "variant already exists!"}), 403

    except Exception as e:
        app.logger.error(e)
        return jsonify({"message": e}), 400


@app.route("/vote", methods=["POST"])
def add_vote():
    try:
        values = request.values.to_dict()
        variant = values["variant"]
        vote = VoteEnum(int(values["vote"]))
        name = values["name"]

        success, message = _add_vote(variant, name, vote)
        return jsonify({"message": message}), 200 if success else 403

    except KeyError as e:
        app.logger.error(e)
        return jsonify({"message": f"missing the required value for {e}"}), 400

    except ValueError as e:
        app.logger.error(e)
        return jsonify({"message": "unexpected value for the vote"}), 400

    except Exception as e:
        app.logger.error(e)
        return jsonify({"message": e}), 400


with app.app_context():
    sa.create_all()

if __name__ == "__main__":
    app.run()
