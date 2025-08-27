from app import app, db, User
from sqlalchemy import text
from werkzeug.security import generate_password_hash

with app.app_context():
    # Apagar todos os usuários
    db.session.query(User).delete()

    # Apagar todo o ranking
    db.session.execute(text("DELETE FROM ranking"))

    # Recriar admin
    admin = User(
        name="admin",
        email="admin@example.com",
        password_hash=generate_password_hash("admin123")
    )
    db.session.add(admin)

    db.session.commit()

    print("✅ Usuários e ranking resetados. Admin recriado (login: admin / senha: admin123)")
