import os
import random
import json
import unicodedata
import re
from datetime import datetime, timedelta
from sqlalchemy import func
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# ----------------------
# App config
# ----------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("PERFUT_SECRET", "dev-secret-change-me")

db_url = os.getenv("DATABASE_URL", "sqlite:///perfut.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Config email
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USER")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASS")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USER")

mail = Mail(app)
s = URLSafeTimedSerializer(app.config["SECRET_KEY"])

# ----------------------
# Models
# ----------------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    coins = db.Column(db.Integer, default=50)
    level = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)


class Card(db.Model):
    __tablename__ = "cards"
    id = db.Column(db.Integer, primary_key=True)
    theme = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    answer = db.Column(db.String(120), nullable=False)
    hints_json = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.Integer, default=1)

    @property
    def hints(self):
        return json.loads(self.hints_json)


class Game(db.Model):
    __tablename__ = "games"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rounds_count = db.Column(db.Integer, default=5)
    themes_json = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="active")
    user_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="games")

    @property
    def themes(self):
        return json.loads(self.themes_json)


class Round(db.Model):
    __tablename__ = "rounds"
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    card_id = db.Column(db.Integer, db.ForeignKey("cards.id"), nullable=False)
    requested_hints = db.Column(db.Integer, default=0)
    used_extra_hints = db.Column(db.Integer, default=0)
    user_guess = db.Column(db.String(120))
    user_points = db.Column(db.Integer, default=0)
    finished = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ends_at = db.Column(db.DateTime)

    game = db.relationship("Game", backref="rounds")
    card = db.relationship("Card")

# ----------------------
# Utilities
# ----------------------
THEMES = [
    ("time", "Time"),
    ("jogador_atividade", "Jogador em atividade"),
    ("jogador_aposentado", "Jogador aposentado"),
    ("estadio", "Estádio"),
    ("tecnico", "Técnicos"),
    ("ano", "Ano"),  # novo tema adicionado
]

def card_points(hints_used: int) -> int:
    base = 10 - max(hints_used - 1, 0)
    return max(base, 1)

def require_login():
    if "user_id" not in session:
        flash("Faça login para jogar.", "warning")
        return False
    return True

def normalize(text: str) -> str:
    text = ''.join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != 'Mn'
    )
    text = re.sub(r'[^a-z0-9 ]', '', text.lower())
    return re.sub(r'\s+', ' ', text).strip()

def is_admin():
    return "user_id" in session and session["user_id"] == 1

# Atualiza nível do usuário com base nos pontos acumulados
def update_user_level(user):
    total_score = sum(game.user_score for game in user.games)
    new_level = total_score // 100 + 1
    if new_level > user.level:
        user.level = new_level
        db.session.commit()
        flash(f"🎉 Parabéns! Você subiu para o nível {new_level}!", "success")

# ----------------------
# Auth routes
# ----------------------
# (registro, login, logout e reset de senha mantidos iguais ao código original)
# ...

# ----------------------
# Index & setup
# ----------------------
@app.route("/")
def index():
    user = None
    if "user_id" in session:
        user = User.query.get(session["user_id"])
    return render_template("index.html", user=user, themes=THEMES)

@app.route("/game_setup", methods=["GET", "POST"])
def game_setup():
    if not require_login():
        return redirect(url_for("login"))
    if request.method == "POST":
        selected = request.form.getlist("themes")
        valid_themes = [key for key, label in THEMES]
        selected = [t for t in selected if t in valid_themes]
        if not selected:
            flash("Selecione ao menos um tema.", "warning")
            return redirect(url_for("game_setup"))
        g = Game(user_id=session["user_id"], rounds_count=5, themes_json=json.dumps(selected))
        db.session.add(g)
        db.session.commit()
        return redirect(url_for("game_play", game_id=g.id))
    return render_template("game_setup.html", themes=THEMES)

def pick_card_for_theme(theme, difficulty=1):
    q = Card.query.filter_by(theme=theme, difficulty=difficulty)
    return q.order_by(db.func.random()).first()

@app.route("/game/play/<int:game_id>")
def game_play(game_id):
    if not require_login(): 
        return redirect(url_for("login"))
    g = Game.query.get_or_404(game_id)
    user = User.query.get(session["user_id"])
    current_number = len([r for r in g.rounds if r.finished]) + 1
    if current_number > g.rounds_count:
        g.status = "finished"
        db.session.commit()
        update_user_level(user)  # Atualiza nível ao final do jogo
        return redirect(url_for("game_result", game_id=g.id))
    current = Round.query.filter_by(game_id=g.id, number=current_number).first()
    if not current:
        theme = g.themes[(current_number - 1) % len(g.themes)]
        card = pick_card_for_theme(theme)
        if not card:
            flash(f"Nenhum card disponível para o tema '{theme}'.", "warning")
            return redirect(url_for("index"))
        current = Round(game_id=g.id, number=current_number, card_id=card.id,
                        started_at=datetime.utcnow(), ends_at=datetime.utcnow() + timedelta(seconds=60))
        db.session.add(current)
        db.session.commit()
    if datetime.utcnow() > current.ends_at and not current.finished:
        current.finished = True
        db.session.commit()
        flash(f"Tempo esgotado! Resposta era: {current.card.answer}", "danger")
        return redirect(url_for("game_play", game_id=g.id))
    card = current.card
    all_hints = card.hints[:]
    random.shuffle(all_hints)
    hints = all_hints[:current.requested_hints]
    show_answer = current.finished and current.user_guess is not None
    seconds_left = max(0, int((current.ends_at - datetime.utcnow()).total_seconds()))
    round_points = card_points(current.requested_hints)
    return render_template("game.html", game=g, round=current, card=card, hints=hints,
                           seconds_left=seconds_left, show_answer=show_answer, user=user,
                           card_points=round_points)

@app.route("/game/guess/<int:round_id>", methods=["POST"])
def game_guess(round_id):
    if not require_login():
        return redirect(url_for("login"))
    r = Round.query.get_or_404(round_id)
    g = r.game
    if r.finished:
        return redirect(url_for("game_play", game_id=g.id))
    guess = request.form.get("guess", "").strip()
    r.user_guess = guess
    if r.requested_hints == 0:
        r.requested_hints = 1
    correct = normalize(guess) == normalize(r.card.answer)
    r.user_points = card_points(r.requested_hints) if correct else 0
    g.user_score += r.user_points
    r.finished = True
    db.session.commit()
    user = User.query.get(g.user_id)
    update_user_level(user)  # Atualiza nível a cada chute
    if correct:
        flash("Parabéns! Você acertou!", "success")
    else:
        flash(f"Errou! Resposta: {r.card.answer}", "danger")
    return redirect(url_for("game_play", game_id=g.id))

# ----------------------
# Demais rotas (extra_hint, resultado, admin_add_card, ranking etc.) mantidas iguais ao código original
# ----------------------

@app.cli.command("init-db")
def init_db():
    db.drop_all()
    db.create_all()
    print("Banco criado e pronto!")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=8080, debug=False)
