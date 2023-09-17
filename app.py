from enum import IntEnum
from typing import Dict, List, Tuple
from uuid import uuid4

from flask import (
    Flask,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, NoResultFound

app = Flask("coffee")
app.config.from_pyfile("coffee.cfg")
app.config.from_prefixed_env("COFFEE")
app.template_folder = "templates"
app.static_folder = "static"
sa = SQLAlchemy(app)

if app.config.get("SECRET_KEY", None) is None:
    raise RuntimeError("The application config has no SECRET_KEY value")

if app.config.get("ADMIN_TOKEN", None) is None:
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

    return f"<span class='vote {value}'>{value}</span>"


@app.route("/")
def show_overview():
    votes = _get_votes()
    return render_template("overview.jinja", votes=votes)


@app.route("/vote/<string:coffee_variant>", methods=["GET", "POST"])
def vote_form(coffee_variant: str):
    if request.method == "POST":
        success = True
        try:
            values = request.values.to_dict()
            vote = VoteEnum(int(values["vote"]))
            name = values["name"]

            success, message = _add_vote(coffee_variant, name, vote)
            if success:
                flash(message, "message")
                return redirect(url_for("show_overview"))
            else:
                flash(message, "error")

        except KeyError as e:
            flash(f"missing the required value for {e}", "error")

        except ValueError:
            flash("unexpected value for the vote", "error")

        except Exception as e:
            current_app.logger.error(e)
            flash("unexpected error", "error")

        return (
            render_template("vote_form.jinja", coffee_variant=coffee_variant),
            400,
        )

    else:
        return render_template("vote_form.jinja", coffee_variant=coffee_variant)


@app.route("/api/export")
def export():
    votes = {
        variant: {
            vote.name: "+" if vote.vote == VoteEnum.Upvote else "-" for vote in votes
        }
        for variant, votes in _get_votes().items()
    }
    return jsonify(votes)


@app.route("/api/variants", methods=["POST"])
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


@app.route("/api/vote", methods=["POST"])
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
