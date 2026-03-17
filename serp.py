from app import application
from app.db.database import init_db

# Инициализация базы данных
init_db()

if __name__ == "__main__":
    application.run(host="0.0.0.0")
