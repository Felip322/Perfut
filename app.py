import os
import random
import json
import unicodedata
import re
import uuid
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from sqlalchemy.orm import joinedload




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

# Email
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
    coins = db.Column(db.Integer, default=100)
    level = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Novas colunas
    last_login = db.Column(db.DateTime, nullable=True)
    login_streak = db.Column(db.Integer, default=0)

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




class Duel(db.Model):
    __tablename__ = "duels"
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    opponent_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    themes_json = db.Column(db.Text, nullable=False)
    rounds_count = db.Column(db.Integer, default=3)
    status = db.Column(db.String(20), default="waiting")  # waiting, active, finished
    code = db.Column(db.String(8), unique=True, nullable=False)

    creator = db.relationship("User", foreign_keys=[creator_id])
    opponent = db.relationship("User", foreign_keys=[opponent_id])










class Game(db.Model):
    __tablename__ = "games"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rounds_count = db.Column(db.Integer, default=5)
    themes_json = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="active")
    user_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # NOVO: define se é solo ou duelo
    mode = db.Column(db.String(20), default="solo")  # 'solo' ou 'duel'

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

    hints_order_json = db.Column(db.Text)  # <<< novo campo para salvar a ordem sorteada

    game = db.relationship("Game", backref="rounds")
    card = db.relationship("Card")

    @property
    def hints_order(self):
        if self.hints_order_json:
            return json.loads(self.hints_order_json)
        return []
    
    @hints_order.setter
    def hints_order(self, value):
        self.hints_order_json = json.dumps(value, ensure_ascii=False)


class Badge(db.Model):
    __tablename__ = "badges"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    level_required = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Badge {self.name}>"


class DuelScore(db.Model):
    __tablename__ = "duels_scores"
    id = db.Column(db.Integer, primary_key=True)
    duel_id = db.Column(db.Integer, db.ForeignKey("duels.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    score = db.Column(db.Integer, default=0)

    duel = db.relationship("Duel", backref="scores")
    user = db.relationship("User")


class WeeklyEvent(db.Model):
    __tablename__ = "weekly_event"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # <-- adicione esta linha
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    scores = db.relationship("WeeklyScore", backref="event", lazy="dynamic")

    @property
    def is_today_active(self):
        """Verifica se o evento está ativo no dia atual."""
        today = datetime.utcnow().date()
        return self.is_active and self.start_date <= today <= self.end_date

class WeeklyScore(db.Model):
    __tablename__ = "weekly_scores"
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("weekly_event.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    score = db.Column(db.Integer, default=0)
    play_date = db.Column(db.Date, nullable=False)

    player = db.relationship("User")


class Quiz(db.Model):
    __tablename__ = 'quiz'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)  # <- aqui
    option1 = db.Column(db.Text, nullable=False)
    option2 = db.Column(db.Text, nullable=False)
    option3 = db.Column(db.Text, nullable=False)
    option4 = db.Column(db.Text, nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)
    theme = db.Column(db.Text)

class QuizScore(db.Model):
    __tablename__ = "quiz_scores"

    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    played_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # ✅ Adicione esta linha

    user = db.relationship("User", backref="quiz_scores")










# ----------------------
# Utilities
# ----------------------
THEMES = [
    ("clube", "Clube"),
    ("jogador_atividade", "Jogador em atividade"),
    ("jogador_aposentado", "Jogador aposentado"),
    ("estadio", "Estádio"),
    ("tecnico", "Técnico"),
    ("Ano", "Ano"),
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
    text = ''.join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-z0-9 ]', '', text.lower())
    return re.sub(r'\s+', ' ', text).strip()

def is_admin():
    return "user_id" in session and session["user_id"] == 1

def update_user_level(user):
    # Soma todos os pontos das partidas do usuário
    total_score = sum(game.user_score for game in user.games)
    # Calcula o nível (1 nível a cada 100 pontos)
    user.level = total_score // 100 + 1
    db.session.commit()


def update_daily_login(user):
    today = datetime.utcnow().date()
    last_login_date = user.last_login.date() if user.last_login else None

    if last_login_date == today:
        # Já logou hoje
        return 0
    elif last_login_date == today - timedelta(days=1):
        # Streak continua
        user.login_streak += 1
    else:
        # Quebra o streak
        user.login_streak = 1

    # Recompensa por streak
    streak_rewards = [5, 10, 15, 20, 25, 30, 50]
    day_index = min(user.login_streak, len(streak_rewards)) - 1
    coins_earned = streak_rewards[day_index]

    user.coins += coins_earned
    user.last_login = datetime.utcnow()

    db.session.commit()
    return coins_earned








# ----------------------
# Routes (Auth, Game, Admin)
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

        # ----- Enviar e-mail de boas-vindas -----
        try:
            msg = Message(
                subject="Bem-vindo ao PERFUT!",
                recipients=[email],
                html=f"""
                <html>
                  <body style="font-family: Arial, sans-serif; color: #333; text-align: center;">
                    <img src="https://perfut-1.onrender.com/static/logo.png" alt="Logo PERFUT" width="150" style="margin-bottom: 20px;">
                    <h2>Olá, {name}!</h2>
                    <p>Obrigado por se cadastrar no <strong>PERFUT</strong>! 🎉</p>
                    <p>Divirta-se e boa sorte nos seus jogos!</p>
                  </body>
                </html>
                """
            )
            mail.send(msg)
        except Exception as e:
            print("Erro ao enviar e-mail de boas-vindas:", e)
            flash("Cadastro realizado, mas não foi possível enviar o e-mail de boas-vindas.", "warning")

        flash("Cadastro realizado! Boa sorte no PERFUT!", "success")
        return redirect(url_for("game_mode_select"))

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
        # Redireciona para escolha de modo após login
        return redirect(url_for("game_mode_select"))
    return render_template("login.html")


@app.route("/game/mode")
def game_mode_select():
    if not require_login():
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    today = datetime.utcnow().date()

    # Atualiza login diário e pega moedas ganhas
    daily_coins = update_daily_login(user)

    # Busca todos eventos ativos no período
    events_today = WeeklyEvent.query.filter(
        WeeklyEvent.is_active == True,
        WeeklyEvent.start_date <= today,
        WeeklyEvent.end_date >= today
    ).all()

    # Lista de eventos que o usuário já jogou hoje
    played_events = [
        score.event_id for score in WeeklyScore.query.filter_by(
            player_id=user.id,
            play_date=today
        ).all()
    ]

    return render_template(
        "game_mode.html",
        user=user,
        hide_ranking=True,
        events_today=events_today,
        played_events=played_events,
        daily_coins=daily_coins  # Passando para o template
    )



@app.route("/duel/join/<code>")
def duel_join(code):
    if not require_login():
        return redirect(url_for("login"))

    duel = Duel.query.filter_by(code=code).first_or_404()

    if duel.opponent_id:
        flash("Este duelo já está completo.", "warning")
        return redirect(url_for("game_mode_select"))

    duel.opponent_id = session["user_id"]
    duel.status = "active"

    # Cria jogos para os dois
    creator_game = Game(user_id=duel.creator_id, rounds_count=duel.rounds_count, themes_json=duel.themes_json)
    opponent_game = Game(user_id=duel.opponent_id, rounds_count=duel.rounds_count, themes_json=duel.themes_json)
    db.session.add_all([creator_game, opponent_game])
    db.session.commit()

    flash("Você entrou no duelo!", "success")
    return redirect(url_for("game_play", game_id=opponent_game.id))


# Página de espera do duelo
@app.route("/duel/wait/<int:duel_id>")
def duel_wait(duel_id):
    if not require_login():
        return redirect(url_for("login"))

    duel = Duel.query.get_or_404(duel_id)
    user = User.query.get(session["user_id"])

    # Se for requisição AJAX
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        if duel.opponent_id:  # adversário entrou
            # Pega o jogo do usuário logado
            if user.id == duel.creator_id:
                game = Game.query.filter_by(user_id=duel.creator_id, mode="duel").order_by(Game.id.desc()).first()
            else:
                game = Game.query.filter_by(user_id=duel.opponent_id, mode="duel").order_by(Game.id.desc()).first()
            return {"status": "active", "game_id": game.id}

        return {"status": "waiting"}

    # Página normal
    return render_template("duel_wait.html", duel=duel, user=user)


    # Página normal
    # Se o usuário terminou o jogo mas o outro não, mostra template de espera pós partida
    user_game = Game.query.filter_by(user_id=user.id).order_by(Game.id.desc()).first()
    if user_game.status == "finished" and (duel.opponent_id is None or Game.query.filter_by(user_id=duel.opponent_id).first().status != "finished"):
        return render_template("duel_wait_finish.html", duel=duel)

    return render_template("duel_wait.html", duel=duel, user=user)

@app.route("/weekly_event")
def weekly_event():
    if not require_login():
        return redirect(url_for("login"))
    
    user = User.query.get(session["user_id"])
    today = datetime.utcnow().date()
    
    # Pega evento ativo
    event = WeeklyEvent.query.filter_by(is_active=True).first()
    
    # Verifica se já jogou hoje
    already_played = False
    if event:
        already_played = WeeklyScore.query.filter_by(event_id=event.id, player_id=user.id, play_date=today).first() is not None
    
    return render_template("weekly_event.html", user=user, already_played=already_played, event=event)


@app.route("/weekly_event/start")
def weekly_event_start():
    if not require_login():
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    today = datetime.utcnow().date()

    # Busca o evento ativo do dia
    weekly_events = WeeklyEvent.query.filter_by(is_active=True).all()
    event = next((e for e in weekly_events if e.is_today_active), None)

    if not event:
        flash("Nenhum evento ativo no momento.", "warning")
        return redirect(url_for("index"))

    # Verifica se já jogou hoje
    if WeeklyScore.query.filter_by(event_id=event.id, player_id=user.id, play_date=today).first():
        flash("Você já jogou hoje!", "info")
        return redirect(url_for("weekly_event"))

    # Cria jogo do evento semanal com 10 perguntas
    g = Game(
        user_id=user.id,
        rounds_count=10,
        themes_json=json.dumps([key for key, _ in THEMES]),
        mode="weekly"  # <-- sem event_id aqui
    )
    db.session.add(g)
    db.session.commit()

    # Marca que o jogador já iniciou hoje
    score_entry = WeeklyScore(
        event_id=event.id,
        player_id=user.id,
        play_date=today
    )
    db.session.add(score_entry)
    db.session.commit()

    flash("Desafio diário iniciado!", "success")
    return redirect(url_for("game_play", game_id=g.id))




@app.route("/game_finish/<int:game_id>")
def game_finish(game_id):
    # Pega o jogo
    game = Game.query.get(game_id)
    if not game:
        flash("Jogo não encontrado.", "error")
        return redirect(url_for("index"))

    # Pega o usuário
    user = User.query.get(game.user_id)

    # Calcula a pontuação final do jogo
    final_score = game.calculate_score()  # sua função de cálculo de pontos

    # ================================
    # Atualiza o score do WeeklyEvent
    # ================================
    if game.mode == "weekly":
        today = datetime.utcnow().date()

        # Busca o evento ativo hoje
        weekly_events = WeeklyEvent.query.filter_by(is_active=True).all()
        event = next((e for e in weekly_events if e.is_today_active), None)

        if event:
            # Busca o registro do jogador no evento
            weekly_score = WeeklyScore.query.filter_by(
                player_id=user.id,
                event_id=event.id,
                play_date=today
            ).first()

            if weekly_score:
                # Atualiza o score existente
                weekly_score.score = final_score
                print(f"Atualizando score do jogador {user.id} para {final_score}")
            else:
                # Cria um novo registro se não existir
                weekly_score = WeeklyScore(
                    player_id=user.id,
                    event_id=event.id,
                    play_date=today,
                    score=final_score
                )
                db.session.add(weekly_score)
                print(f"Criando score do jogador {user.id} com {final_score}")

            db.session.commit()

        flash(f"Jogo finalizado! Você marcou {final_score} pontos no evento semanal.", "success")
        return redirect(url_for("weekly_result", event_id=event.id))

    # ================================
    # Fluxo de duelo
    # ================================
    elif game.mode == "duel":
        duel = Duel.query.filter(
            (Duel.creator_id == game.user_id) | (Duel.opponent_id == game.user_id)
        ).order_by(Duel.id.desc()).first()

        flash(f"Jogo finalizado! Você marcou {final_score} pontos no duelo.", "success")
        return redirect(url_for("duel_result", duel_id=duel.id))

    # ================================
    # Fluxo padrão (solo/torneio)
    # ================================
    else:
        flash(f"Jogo finalizado! Você marcou {final_score} pontos.", "success")
        return redirect(url_for("game_result", game_id=game.id))





@app.route("/weekly_result/<int:event_id>")
def weekly_result(event_id):
    if not require_login():
        return redirect(url_for("login"))

    event = WeeklyEvent.query.get_or_404(event_id)

    # Pega todos os scores do evento
    scores = WeeklyScore.query.filter_by(event_id=event.id).order_by(WeeklyScore.score.desc()).all()

    user_score = WeeklyScore.query.filter_by(event_id=event.id, user_id=session["user_id"]).first()

    return render_template(
        "weekly_result.html",
        event=event,
        scores=scores,
        user_score=user_score
    )





@app.route("/game/duel_setup", methods=["GET", "POST"])
def game_duel_setup():
    if not require_login():
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        # Custo do duelo
        cost = 5
        if user.coins < cost:
            flash(f"Você precisa de {cost} moedas para criar um duelo.", "warning")
            return redirect(url_for("game_duel_setup"))

        # Deduz as moedas
        user.coins -= cost
        db.session.commit()
        flash(f"Você gastou {cost} moedas para criar o duelo.", "info")

        selected = request.form.getlist("themes")
        valid_themes = [key for key, _ in THEMES]
        selected = [t for t in selected if t in valid_themes]
        if not selected:
            flash("Selecione ao menos um tema.", "warning")
            return redirect(url_for("game_duel_setup"))

        rounds_count = int(request.form.get("rounds", 3))

        duel_code = str(uuid.uuid4())[:8].upper()
        duel = Duel(
            creator_id=user.id,
            themes_json=json.dumps(selected),
            rounds_count=rounds_count,
            code=duel_code,
            status="waiting"
        )
        db.session.add(duel)
        db.session.commit()

        # Cria imediatamente o jogo do criador, mas sem começar o duelo ainda
        creator_game = Game(
            user_id=user.id,
            rounds_count=rounds_count,
            themes_json=duel.themes_json,
            mode="duel"
        )
        db.session.add(creator_game)
        db.session.commit()

        flash(f"Duelo criado! Compartilhe o código: {duel_code}", "info")

        return redirect(url_for("duel_wait", duel_id=duel.id))

    return render_template("duel_setup.html", user=user, themes=THEMES, rounds=3)





@app.route("/game/duel_join", methods=["GET", "POST"], endpoint="duel_join_page")
def duel_join_page():
    if not require_login():
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        # Custo para entrar no duelo
        cost = 5
        if user.coins < cost:
            flash(f"Você precisa de {cost} moedas para entrar no duelo.", "warning")
            return redirect(url_for("duel_join_page"))

        code = request.form.get("code", "").strip().upper()
        duel = Duel.query.filter_by(code=code, status="waiting").first()
        if not duel:
            flash("Código inválido ou duelo já começou.", "danger")
            return redirect(url_for("duel_join_page"))

        if duel.creator_id == user.id:
            flash("Você não pode entrar no próprio duelo.", "warning")
            return redirect(url_for("duel_join_page"))

        # Deduz as moedas do oponente
        user.coins -= cost
        db.session.commit()
        flash(f"Você gastou {cost} moedas para entrar no duelo.", "info")

        duel.opponent_id = user.id
        duel.status = "active"
        db.session.commit()

        # Cria o jogo do criador se ainda não existir
        creator_game = Game.query.filter_by(
            user_id=duel.creator_id,
            rounds_count=duel.rounds_count,
            themes_json=duel.themes_json
        ).first()
        if not creator_game:
            creator_game = Game(
                user_id=duel.creator_id,
                rounds_count=duel.rounds_count,
                themes_json=duel.themes_json,
                mode="duel"
            )
            db.session.add(creator_game)

        # Cria o jogo do oponente
        opponent_game = Game(
            user_id=duel.opponent_id,
            rounds_count=duel.rounds_count,
            themes_json=duel.themes_json,
            mode="duel"
        )
        db.session.add(opponent_game)
        db.session.commit()

        flash(f"Duelo iniciado! Boa sorte!", "success")
        return redirect(url_for("game_play", game_id=opponent_game.id))

    return render_template("duel_join.html", user=user)




@app.route("/duel/result/<int:duel_id>")
def duel_result(duel_id):
    # Busca o duelo ou retorna 404 se não existir
    duel = Duel.query.get_or_404(duel_id)
    
    # Pega os jogos mais recentes de cada jogador
    creator_game = Game.query.filter_by(user_id=duel.creator_id).order_by(Game.id.desc()).first()
    opponent_game = Game.query.filter_by(user_id=duel.opponent_id).order_by(Game.id.desc()).first()

    # Pontuação de cada jogador (0 se não houver jogo)
    creator_score = creator_game.user_score if creator_game else 0
    opponent_score = opponent_game.user_score if opponent_game else 0

    # Atualiza a tabela DuelScore
    DuelScore.query.filter_by(duel_id=duel.id).delete()
    db.session.add_all([
        DuelScore(duel_id=duel.id, user_id=duel.creator_id, score=creator_score),
        DuelScore(duel_id=duel.id, user_id=duel.opponent_id, score=opponent_score)
    ])
    db.session.commit()

    # Determina o vencedor
    winner = None
    if creator_score > opponent_score:
        winner = duel.creator
    elif opponent_score > creator_score:
        winner = duel.opponent

    # Pega badges do banco
    def get_badge(score):
        badge = ""
        badges = Badge.query.order_by(Badge.level_required.desc()).all()
        for b in badges:
            if score >= b.level_required:
                badge = b.name
                break
        return badge

    creator_badge = get_badge(creator_score)
    opponent_badge = get_badge(opponent_score)

    return render_template(
        "duel_result.html",
        duel=duel,
        creator_score=creator_score,
        opponent_score=opponent_score,
        winner=winner,
        creator_badge=creator_badge,
        opponent_badge=opponent_badge
    )



@app.route("/weekly_ranking")
def weekly_ranking():
    if not require_login():
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    today = datetime.utcnow().date()
    week_start = today - timedelta(days=today.weekday())  # segunda-feira
    week_end = week_start + timedelta(days=6)             # domingo

    event = WeeklyEvent.query.filter_by(is_active=True).first()
    scores = []

    if event:
        # Agrupa scores da semana por jogador
        scores = (
            db.session.query(
                User.id,
                User.name,
                func.sum(WeeklyScore.score).label("total_score")
            )
            .join(User, User.id == WeeklyScore.player_id)
            .filter(
                WeeklyScore.event_id == event.id,
                WeeklyScore.play_date.between(week_start, week_end)
            )
            .group_by(User.id, User.name)
            .order_by(func.sum(WeeklyScore.score).desc(), User.name.asc())
            .all()
        )

    return render_template("weekly_ranking.html", scores=scores, event=event, user=user)










@app.route("/quiz/<int:question_id>")
def quiz_play(question_id):
    if not require_login():
        return redirect(url_for("login"))

    question_ids = session.get('quiz_question_ids')

    if not question_ids:
        # Se não tiver quiz em andamento, inicia automaticamente
        return redirect(url_for('quiz_start'))

    if question_id not in question_ids:
        flash("Pergunta inválida ou quiz já encerrado.", "warning")
        return redirect(url_for("quiz_start"))

    current_index = question_ids.index(question_id)
    session['quiz_current_index'] = current_index

    question = Quiz.query.get_or_404(question_id)
    session[f'quiz_question_start_{question_id}'] = datetime.utcnow().isoformat()

    return render_template(
        "quiz.html",
        question=question,
        current_index=current_index + 1,
        total=len(question_ids)
    )




# Página inicial do quiz
@app.route("/quiz/start_page")
def quiz_start_page():
    if not require_login():
        return redirect(url_for("login"))

    # Pega a primeira pergunta disponível
    first_question = Quiz.query.order_by(Quiz.id).first()
    if not first_question:
        flash("O quiz ainda não tem perguntas cadastradas.", "warning")
        return redirect(url_for("index"))

    user = User.query.get(session["user_id"])  # pega o usuário logado

    return render_template(
        "quiz_start.html",
        first_question_id=first_question.id,
        user=user,
        quiz_mode=True,       # habilita menu do quiz
        event_weekly=False,   # não é evento semanal
        hide_ranking=False    # mostra ranking
    )


# Inicia o quiz (após clicar "Começar Quiz" na página inicial)
@app.route("/quiz/start")
def quiz_start():
    if not require_login():
        return redirect(url_for("login"))

    session['quiz_score'] = 0
    session['quiz_current_index'] = 0

    # Seleciona 10 perguntas aleatórias
    all_questions = Quiz.query.order_by(db.func.random()).limit(10).all()
    if not all_questions:
        flash("Nenhuma pergunta disponível.", "warning")
        return redirect(url_for("quiz_start_page"))

    # Salva IDs em sessão
    session['quiz_question_ids'] = [q.id for q in all_questions]

    # Redireciona para a primeira pergunta
    first_question_id = session['quiz_question_ids'][0]
    return redirect(url_for("quiz_play", question_id=first_question_id))




@app.route('/quiz/answer/<int:question_id>', methods=['POST'])
def quiz_answer(question_id):
    if not require_login():
        return redirect(url_for("login"))

    data = request.get_json()
    selected_option = int(data.get("selected_option"))

    question = Quiz.query.get_or_404(question_id)
    correct = (selected_option == question.correct_option)

    if correct:
        session['quiz_score'] = session.get('quiz_score', 0) + 1

    # Atualiza índice para próxima pergunta
    current_index = session.get('quiz_current_index', 0)
    session['quiz_current_index'] = current_index + 1

    question_ids = session.get('quiz_question_ids', [])
    if current_index + 1 < len(question_ids):
        next_question_id = question_ids[current_index + 1]
        next_question_url = url_for('quiz_play', question_id=next_question_id)
    else:
        next_question_url = url_for('quiz_result')

    return {
        "correct": correct,
        "correct_answer": getattr(question, f"option{question.correct_option}"),
        "next_question_url": next_question_url
    }



@app.route("/quiz/result", methods=["GET", "POST"])
def quiz_result():
    if 'quiz_score' not in session or 'quiz_question_ids' not in session:
        flash("Nenhum quiz em andamento.", "warning")
        return redirect(url_for("game_mode_select"))

    score = session.get('quiz_score', 0)
    total = len(session.get('quiz_question_ids', []))
    user = User.query.get(session["user_id"])

    # Atualiza ou cria o registro de QuizScore
    quiz_score = QuizScore.query.filter_by(user_id=user.id).first()

    if quiz_score:
        quiz_score.score += score  # soma ao que já tinha
        quiz_score.played_at = datetime.utcnow()
    else:
        quiz_score = QuizScore(
            user_id=user.id,
            score=score,
            played_at=datetime.utcnow()
        )
        db.session.add(quiz_score)

    db.session.commit()

    # Limpa sessão do quiz
    for key in ['quiz_score', 'quiz_current_index', 'quiz_question_ids']:
        session.pop(key, None)

    return render_template("quiz_result.html", score=score, total=total, user=user)


@app.route('/quiz/ranking')
def quiz_ranking():
    # Pegar top 10 pontuações acumuladas e já carregar o usuário relacionado
    top_scores = (
        QuizScore.query
        .options(joinedload(QuizScore.user))  # evita N+1 queries
        .order_by(QuizScore.score.desc(), QuizScore.played_at.desc())
        .limit(10)
        .all()
    )

    user = None
    if "user_id" in session:
        user = User.query.get(session["user_id"])

    return render_template('quiz_ranking.html', scores=top_scores, user=user)








@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("index"))


@app.route("/") 
def index():
    user = None 
    if "user_id" in session: user = User.query.get(session["user_id"]) 
    return render_template("index.html", user=user, themes=THEMES)


# --- Reset & Forgot Password
@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        email = s.loads(token, salt="password-reset", max_age=3600)
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
                    body=f"Olá {user.name},\n\nPara redefinir sua senha clique no link abaixo (expira em 1 hora):\n{reset_url}\n\nSe não foi você, ignore este e-mail."
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

    # Subquery: total de pontos por usuário
    score_sum = (
        db.session.query(
            Game.user_id,
            func.coalesce(func.sum(Game.user_score), 0).label("total_score")
        )
        .group_by(Game.user_id)
        .subquery()
    )

    # Busca usuários que jogaram (total_score > 0)
    rows = (
        db.session.query(
            User.id,
            User.name,
            User.coins,
            User.level,
            func.coalesce(score_sum.c.total_score, 0).label("total_score")
        )
        .outerjoin(score_sum, User.id == score_sum.c.user_id)
        .filter(func.coalesce(score_sum.c.total_score, 0) > 0)
        .order_by(
            User.level.desc(),
            func.coalesce(score_sum.c.total_score, 0).desc(),
            User.coins.desc(),
            User.name.asc()
        )
        .all()
    )

    rankings = []
    for user_id, name, coins, level, total_score in rows:
        # Atualiza nível do usuário se necessário
        new_level = total_score // 100 + 1
        if level != new_level:
            user = User.query.get(user_id)
            user.level = new_level
            db.session.commit()
            level = new_level

        # Busca badge correspondente ao nível
        badge = (
            db.session.query(Badge)
            .filter(Badge.level_required <= level)
            .order_by(Badge.level_required.desc())
            .first()
        )
        badge_name = badge.name if badge else ""
        rankings.append((name, int(total_score), level, badge_name))

    # Usuário atual
    current_user = User.query.get(session["user_id"])
    if not current_user:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("login"))

    return render_template("ranking.html", rankings=rankings, user=current_user)








# --- Game Setup & Play
@app.route("/game_setup", methods=["GET", "POST"])
def game_setup():
    if not require_login():
        return redirect(url_for("login"))
    
    user = User.query.get(session["user_id"])

    if request.method == "POST":
        # Custo da partida
        cost = 5
        if user.coins < cost:
            flash(f"Você precisa de {cost} moedas para iniciar uma partida.", "warning")
            return redirect(url_for("index"))
        
        # Deduz as moedas
        user.coins -= cost
        db.session.commit()

        selected = request.form.getlist("themes")
        valid_themes = [key for key, label in THEMES]
        selected = [t for t in selected if t in valid_themes]
        if not selected:
            flash("Selecione ao menos um tema.", "warning")
            return redirect(url_for("game_setup"))
        
        rounds_count = int(request.form.get("rounds", 5))  # lê o input do form

        g = Game(
            user_id=session["user_id"],
            rounds_count=rounds_count,
            themes_json=json.dumps(selected)
        )
        db.session.add(g)
        db.session.commit()
        flash(f"Você gastou {cost} moedas para iniciar a partida.", "info")
        return redirect(url_for("game_play", game_id=g.id))
    
    return render_template("game.html", themes=THEMES, user=user)




def pick_card_for_theme(theme, difficulty=1):
    q = Card.query.filter_by(theme=theme, difficulty=difficulty)
    return q.order_by(db.func.random()).first()


@app.route("/game/result/<int:game_id>")
def game_result(game_id):
    if not require_login():
        return redirect(url_for("login"))

    game = Game.query.get_or_404(game_id)
    user = User.query.get(session["user_id"])

    # Busca badges do banco
    badges = Badge.query.order_by(Badge.level_required).all()

    badge_levels = {b.level_required: b.name for b in badges}


    # Calcula pontos totais do jogador nessa partida
    user_score = game.user_score  # ajuste conforme sua lógica de pontos
    earned_badges = [name for level, name in badge_levels.items() if user_score >= level]

    return render_template(
        "result.html",
        game=game,
        user=user,
        earned_badges=earned_badges
    )








@app.route("/game/play/<int:game_id>")
def game_play(game_id):
    if not require_login():
        return redirect(url_for("login"))

    g = Game.query.get_or_404(game_id)
    user = User.query.get(session["user_id"])

    # Determina a rodada atual
    current_number = len([r for r in g.rounds if r.finished]) + 1
    if current_number > g.rounds_count:
        g.status = "finished"
        db.session.commit()

        # Se for duelo, verifica status do duelo
        if g.mode == "duel":
            duel = Duel.query.filter(
                ((Duel.creator_id == g.user_id) | (Duel.opponent_id == g.user_id)),
                Duel.status.in_(["active", "finished"])
            ).order_by(Duel.id.desc()).first()

            if duel:
                creator_game = Game.query.filter_by(user_id=duel.creator_id).order_by(Game.id.desc()).first()
                opponent_game = Game.query.filter_by(user_id=duel.opponent_id).order_by(Game.id.desc()).first()

                if creator_game.status == "finished" and opponent_game.status == "finished":
                    duel.status = "finished"
                    db.session.commit()
                    return redirect(url_for("duel_result", duel_id=duel.id))
                else:
                    flash("Você terminou, mas aguarde seu oponente terminar o duelo.", "info")
                    return redirect(url_for("duel_wait", duel_id=duel.id))

        # Para solo/torneio
        return redirect(url_for("game_result", game_id=g.id))

    # Busca ou cria a rodada atual
    current = Round.query.filter_by(game_id=g.id, number=current_number).first()
    if not current:
        if g.mode == "duel":
            duel = Duel.query.filter(
                (Duel.creator_id == g.user_id) | (Duel.opponent_id == g.user_id)
            ).first()

            # Cria lista de cartas do duelo se ainda não existir
            if not getattr(duel, "cards_order_json", None):
                cards = []
                themes = g.themes
                for i in range(duel.rounds_count):
                    theme = themes[i % len(themes)]
                    card = Card.query.filter_by(theme=theme, difficulty=1).order_by(db.func.random()).first()
                    cards.append(card.id)
                duel.cards_order_json = json.dumps(cards)
                db.session.commit()

            cards_order = json.loads(duel.cards_order_json)
            card_id = cards_order[current_number - 1]
            card = Card.query.get(card_id)
        else:
            # Solo/torneio: carta sem repetição
            theme = g.themes[(current_number - 1) % len(g.themes)]
            used_card_ids = [r.card_id for r in g.rounds]
            card = Card.query.filter_by(theme=theme, difficulty=1).filter(~Card.id.in_(used_card_ids)).order_by(db.func.random()).first()

        if not card:
            flash("Nenhum card disponível.", "warning")
            return redirect(url_for("index"))

        # Embaralha as dicas
        hints_order = card.hints[:]
        random.shuffle(hints_order)

        current = Round(
            game_id=g.id,
            number=current_number,
            card_id=card.id,
            started_at=datetime.utcnow(),
            ends_at=datetime.utcnow() + timedelta(seconds=300),
            hints_order_json=json.dumps(hints_order, ensure_ascii=False)
        )
        db.session.add(current)
        db.session.commit()

    # Verifica tempo da rodada
    if datetime.utcnow() > current.ends_at and not current.finished:
        current.finished = True
        db.session.commit()
        flash(f"Tempo esgotado! Resposta era: {current.card.answer}", "danger")
        return redirect(url_for("game_play", game_id=g.id))

    hints_order = json.loads(current.hints_order_json or "[]")
    hints = hints_order[:current.requested_hints]

    show_answer = current.finished and current.user_guess is not None
    seconds_left = max(0, int((current.ends_at - datetime.utcnow()).total_seconds()))
    round_points = card_points(current.requested_hints)

    return render_template(
        "game.html",
        game=g,
        round=current,
        card=current.card,
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
    user = User.query.get(g.user_id)
    # pega o usuário da partida
    if r.finished:
        return redirect(url_for("game_play", game_id=g.id))
    guess = request.form.get("guess", "").strip()
    r.user_guess = guess
    if r.requested_hints == 0:
        r.requested_hints = 1
    # Verifica se acertou
    correct = normalize(guess) == normalize(r.card.answer)
    r.user_points = card_points(r.requested_hints) if correct else 0
    g.user_score += r.user_points
    r.finished = True
    db.session.commit()

    # Atualiza o nível do usuário
    old_level = user.level
    total_score = sum(game.user_score for game in user.games)
    user.level = total_score // 100 + 1
    db.session.commit()

    # Mensagem de nível up
    if user.level > old_level:
        flash(f"🎉 Parabéns! Você subiu para o nível {user.level}!", "success")
    
    # Mensagem de acerto/erro
    flash(
        "Parabéns! Você acertou!" if correct else f"Errou! Resposta: {r.card.answer}",
        "success" if correct else "danger"
    )
    return redirect(url_for("game_play", game_id=g.id))


@app.route("/game/hint/<int:round_id>", methods=["POST"])
def game_hint(round_id):
    if not require_login():
        return redirect(url_for("login"))

    r = Round.query.get_or_404(round_id)

    if r.finished:
        return redirect(url_for("game_play", game_id=r.game_id))

    # Limita o máximo de 10 dicas normais
    if r.requested_hints < 10:
        r.requested_hints += 1
        db.session.commit()
        flash("Dica liberada! Veja abaixo.", "info")
    else:
        flash("Máximo de dicas atingido.", "warning")

    return redirect(url_for("game_play", game_id=r.game_id))




@app.route("/game/extra_hint/<int:round_id>", methods=["POST"])
def game_extra_hint(round_id):
    if not require_login():
        return redirect(url_for("login"))
    
    r = Round.query.get_or_404(round_id)
    user = User.query.get(session["user_id"])
    
    # Verifica se já foi usada a dica extra
    if r.used_extra_hints >= 1:
        flash("Você já usou a dica extra nesta rodada.", "warning")
        return redirect(url_for("game_play", game_id=r.game_id))
    
    cost = 5
    if user.coins < cost:
        flash("Moedas insuficientes para dica extra.", "warning")
        return redirect(url_for("game_play", game_id=r.game_id))
    
    user.coins -= cost
    r.used_extra_hints = 1  # marca como usada
    db.session.commit()
    flash("Dica extra liberada! Veja abaixo.", "success")
    return redirect(url_for("game_play", game_id=r.game_id))


    # --- Cálculo de level up ---
    total_score = sum(game.user_score for game in user.games)
    new_level = total_score // 100 + 1
    old_level = user.level
    level_up = new_level > old_level
    user.level = new_level
    db.session.commit()

    # --- Atualização da pontuação semanal ---
    if g_game.mode == "weekly":
        today = datetime.utcnow().date()
        event = WeeklyEvent.query.filter_by(is_active=True).first()
        if event:
            ws = WeeklyScore.query.filter_by(
                event_id=event.id,
                player_id=user.id,
                play_date=today
            ).first()
            if ws:
                ws.score = g_game.user_score
            else:
                ws = WeeklyScore(
                    event_id=event.id,
                    player_id=user.id,
                    score=g_game.user_score,
                    play_date=today
                )
                db.session.add(ws)
            db.session.commit()

    # --- Recompensa de moedas pelo desempenho ---
    total_coins = 0
    for r in g_game.rounds:
        if r.user_points > 0:  # acertou
            # 1 dica → 100, 2 dicas → 90, 3 → 80, ..., 10 → 10 moedas
            coins = max(110 - r.requested_hints * 10, 10)
            total_coins += coins

    user.coins += total_coins
    db.session.commit()
    flash(f"Você ganhou {total_coins} moedas pelo desempenho!", "success")

    return render_template(
        "result.html",
        game=g_game,
        user=user,
        level_up=level_up,
        new_level=new_level
    )


# @app.route("/coins/watch-ad", methods=["POST"])
# def watch_ad():
#     if not require_login():
#         return redirect(url_for("login"))
#     user = User.query.get(session["user_id"])
#     user.coins += 10
#     db.session.commit()
#     flash("Obrigado por assistir! Você ganhou 10 moedas.", "success")
#     return redirect(url_for("index"))

@app.route("/game/skip/<int:round_id>", methods=["POST"])
def game_skip(round_id):
    if not require_login():
        return redirect(url_for("login"))

    r = Round.query.get_or_404(round_id)
    g = r.game
    user = User.query.get(session["user_id"])

    if r.finished:
        flash("Esta rodada já foi finalizada.", "warning")
        return redirect(url_for("game_play", game_id=g.id))

    # Marca a rodada como finalizada sem pontos
    r.finished = True
    r.user_points = 0
    db.session.commit()
    flash(f"Rodada {r.number} pulada! Sem pontos ganhos.", "info")

    # Verifica se há próxima rodada
    next_number = r.number + 1
    if next_number > g.rounds_count:
        g.status = "finished"
        db.session.commit()
        flash("Última rodada concluída!", "info")

        # Verifica se é um duelo
        duel = Duel.query.filter(
            (Duel.creator_id == g.user_id) | (Duel.opponent_id == g.user_id)
        ).order_by(Duel.id.desc()).first()

        if duel:
            return redirect(url_for("duel_result", duel_id=duel.id))
        else:
            return redirect(url_for("game_result", game_id=g.id))

    # Redireciona para a próxima rodada
    return redirect(url_for("game_play", game_id=g.id))





@app.route("/termos")
def termos():
    return render_template("termos.html")

@app.route("/privacidade")
def privacidade():
    return render_template("privacidade.html")

@app.route("/aviso")
def aviso():
    return render_template("aviso.html")

@app.route("/admin/add-card", methods=["GET", "POST"])
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
            hints_json=json.dumps(hints, ensure_ascii=False),
            difficulty=int(request.form.get("difficulty", 1))
        )
        db.session.add(c)
        db.session.commit()
        flash("Cartinha criada!", "success")
        return redirect(url_for("admin_add_card"))
    return render_template("admin_add_card.html", themes=THEMES)

# --- CLI
@app.cli.command("init-db")
def init_db():
    db.drop_all()
    db.create_all()
    print("Banco criado e pronto!")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=8080, debug=False)
