import os
import random
import json
import unicodedata
import re
from datetime import datetime, timedelta
import socket
import threading
import webbrowser
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

# Usa DATABASE_URL do Render se existir, senão cai no SQLite local
db_url = os.getenv("DATABASE_URL", "sqlite:///perfut.db")

# Render fornece "postgres://", mas SQLAlchemy exige "postgresql://"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

# Config e-mail (exemplo com Gmail, mas pode usar SendGrid, Mailtrap etc.)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USER")   # seu e-mail
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASS")   # senha/app password
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USER")

mail = Mail(app)

# Gerador de tokens
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
    # Remove acentos
    text = ''.join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != 'Mn'
    )
    # Minúsculas e remove tudo que não for letra, número ou espaço
    text = re.sub(r'[^a-z0-9 ]', '', text.lower())
    # Remove múltiplos espaços
    return re.sub(r'\s+', ' ', text).strip()

def is_admin():
    return "user_id" in session and session["user_id"] == 1


# ----------------------
# Auth routes
# ----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        if not name or not email or not password:
            flash("Preencha todos os campos.", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("E-mail já cadastrado.", "danger")
            return redirect(url_for("register"))
        u = User(name=name, email=email)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        session["user_id"] = u.id
        flash("Cadastro realizado! Boa sorte no PERFUT!", "success")
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        u = User.query.filter_by(email=email).first()
        if not u or not u.check_password(password):
            flash("Credenciais inválidas.", "danger")
            return redirect(url_for("login"))
        session["user_id"] = u.id
        flash("Bem-vindo de volta!", "success")
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("index"))


# ----------------------
# Index & setup
# ----------------------
@app.route("/")
def index():
    user = None
    if "user_id" in session:
        user = User.query.get(session["user_id"])
    return render_template("index.html", user=user, themes=THEMES)

@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        email = s.loads(token, salt="password-reset", max_age=3600)  # expira em 1h
    except Exception:
        flash("Link inválido ou expirado.", "danger")
        return redirect(url_for("forgot_password"))

    user = User.query.filter_by(email=email).first_or_404()

    if request.method == "POST":
        new_pwd = request.form["password"]
        user.set_password(new_pwd)
        db.session.commit()
        flash("Senha redefinida com sucesso! Faça login.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html")



@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = s.dumps(email, salt="password-reset")
            reset_url = url_for("reset_password", token=token, _external=True)

            try:
                msg = Message(
                    subject="Redefinição de senha - PERFUT",
                    recipients=[email],
                    body=f"Olá {user.name},\n\n"
                         f"Para redefinir sua senha clique no link abaixo (expira em 1 hora):\n"
                         f"{reset_url}\n\n"
                         "Se não foi você, ignore este e-mail."
                )
                mail.send(msg)
                flash("Enviamos um link de redefinição para seu e-mail.", "info")
            except Exception as e:
                print("Erro ao enviar email:", e)
                flash("Erro ao enviar o e-mail de recuperação.", "danger")
        else:
            flash("E-mail não encontrado.", "danger")
        return redirect(url_for("login"))
    return render_template("forgot_password.html")


@app.route("/ranking")
def ranking():
    if "user_id" not in session:
        flash("Faça login para ver o ranking.", "warning")
        return redirect(url_for("login"))

    # soma dos pontos de todas as partidas por usuário
    score_sum = (
        db.session.query(
            Game.user_id,
            func.coalesce(func.sum(Game.user_score), 0).label("total_score")
        )
        .group_by(Game.user_id)
        .subquery()
    )

    # pega (nome, total_score) e ordena: nível ↓, pontuação ↓, moedas ↓, nome ↑
    rows = (
        db.session.query(
            User.name,
            func.coalesce(score_sum.c.total_score, 0).label("total_score")
        )
        .outerjoin(score_sum, User.id == score_sum.c.user_id)
        .order_by(
            User.level.desc(),
            score_sum.c.total_score.desc(),
            User.coins.desc(),
            User.name.asc()
        )
        .all()
    )

    rankings = [(name, int(total)) for name, total in rows]
    current_user = User.query.get(session["user_id"])

    return render_template("ranking.html", rankings=rankings, user=current_user)

@app.route("/game_setup", methods=["GET", "POST"])
def game_setup():
    if not require_login():
        return redirect(url_for("login"))

    if request.method == "POST":
        # Pega temas enviados pelo formulário
        selected = request.form.getlist("themes")
        valid_themes = [key for key, label in THEMES]
        selected = [t for t in selected if t in valid_themes]

        if not selected:
            flash("Selecione ao menos um tema.", "warning")
            return redirect(url_for("game_setup"))

        # Cria um novo jogo vinculado ao usuário
        g = Game(
            user_id=session["user_id"],
            rounds_count=5,
            themes_json=json.dumps(selected)
        )
        db.session.add(g)
        db.session.commit()

        # Redireciona corretamente para a partida
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

    # Próximo round baseado no número de rounds finalizados
    current_number = len([r for r in g.rounds if r.finished]) + 1

    if current_number > g.rounds_count:
        g.status = "finished"
        db.session.commit()
        return redirect(url_for("game_result", game_id=g.id))

    # Pega o round existente ou cria um novo
    current = Round.query.filter_by(game_id=g.id, number=current_number).first()
    if not current:
        theme = g.themes[(current_number - 1) % len(g.themes)]
        card = pick_card_for_theme(theme)
        if not card:
            flash(f"Nenhum card disponível para o tema '{theme}'.", "warning")
            return redirect(url_for("index"))

        current = Round(
            game_id=g.id,
            number=current_number,
            card_id=card.id,
            started_at=datetime.utcnow(),
            ends_at=datetime.utcnow() + timedelta(seconds=60),  # tempo padrão
        )
        db.session.add(current)
        db.session.commit()

    # Controle de tempo
    if datetime.utcnow() > current.ends_at and not current.finished:
        current.finished = True
        db.session.commit()
        flash(f"Tempo esgotado! Resposta era: {current.card.answer}", "danger")
        return redirect(url_for("game_play", game_id=g.id))

    card = current.card

    # Embaralhar as dicas a cada rodada
    all_hints = card.hints[:]  
    random.shuffle(all_hints)
    hints = all_hints[:current.requested_hints]

    show_answer = current.finished and current.user_guess is not None
    seconds_left = max(0, int((current.ends_at - datetime.utcnow()).total_seconds()))
    round_points = card_points(current.requested_hints)

    return render_template(
        "game.html",
        game=g,
        round=current,
        card=card,
        hints=hints,
        seconds_left=seconds_left,
        show_answer=show_answer,
        user=user,
        card_points=round_points
    )



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

    # Normaliza resposta do usuário e do card
    correct = normalize(guess) == normalize(r.card.answer)
    
    r.user_points = card_points(r.requested_hints) if correct else 0
    g.user_score += r.user_points
    r.finished = True
    db.session.commit()

    if correct:
        flash("Parabéns! Você acertou!", "success")
    else:
        flash(f"Errou! Resposta: {r.card.answer}", "danger")

    return redirect(url_for("game_play", game_id=g.id))



@app.route("/game/extra_hint/<int:round_id>", methods=["POST"])
def game_extra_hint(round_id):
    if not require_login(): return redirect(url_for("login"))
    r = Round.query.get_or_404(round_id)
    user = User.query.get(session["user_id"])
    cost = 5
    if user.coins < cost:
        flash("Moedas insuficientes para dica extra.", "warning")
        return redirect(url_for("game_play", game_id=r.game_id))
    user.coins -= cost
    r.used_extra_hints += 1
    db.session.commit()
    flash("Dica extra comprada! Veja abaixo.", "success")
    return redirect(url_for("game_play", game_id=r.game_id))





@app.route("/game/result/<int:game_id>")
def game_result(game_id):
    g = Game.query.get_or_404(game_id)
    user = User.query.get(g.user_id)
    return render_template("result.html", game=g, user=user)


@app.route("/coins/watch-ad", methods=["POST"])
def watch_ad():
    if not require_login(): return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    user.coins += 10
    db.session.commit()
    flash("Obrigado por assistir! Você ganhou 10 moedas.", "success")
    return redirect(url_for("index"))

@app.route("/termos")
def termos():
    return render_template("termos.html")

@app.route("/privacidade")
def privacidade():
    return render_template("privacidade.html")

@app.route("/aviso")
def aviso():
    return render_template("aviso.html")


@app.route("/admin/add-card", methods=["GET","POST"])
def admin_add_card():
    if not is_admin():
        flash("Acesso negado.", "danger")
        return redirect(url_for("index"))
    if request.method == "POST":
        theme = request.form["theme"]
        title = request.form["title"]
        answer = request.form["answer"]
        hints = [request.form.get(f"hint{i}", "").strip() for i in range(1, 11)]
        hints = [h for h in hints if h]
        c = Card(
    theme=theme,
    title=title,
    answer=answer,
    hints_json=json.dumps(hints, ensure_ascii=False),  # <<< aqui!
    difficulty=int(request.form.get("difficulty", 1))
)

        db.session.add(c)
        db.session.commit()
        flash("Cartinha criada!", "success")
        return redirect(url_for("admin_add_card"))
    return render_template("admin_add_card.html", themes=THEMES)


@app.cli.command("init-db")
def init_db():
    db.drop_all()
    db.create_all()
    print("Banco criado e pronto!")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=8080, debug=False)
