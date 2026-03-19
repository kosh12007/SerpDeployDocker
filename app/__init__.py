from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_caching import Cache
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import secrets
from datetime import datetime, timezone
from app.db_config import LOGGING_ENABLED
import logging

# Инициализация кеша
cache = Cache()

# Инициализация Mail
mail = Mail()

from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

# Инициализация приложения
application = Flask(__name__, static_folder="../static", template_folder="../templates")
# Настройка приложения
from .config import Config, MailConfig  # Импортируем MailConfig

application.config.from_object(Config)

# Применяем ProxyFix для корректной работы через Nginx (определение https)
application.wsgi_app = ProxyFix(application.wsgi_app, x_proto=1, x_host=1)

# Устанавливаем секретный ключ из загруженной конфигурации
application.secret_key = application.config["SECRET_KEY"]

# Вручную обновляем application.config значениями из MailConfig, если они определены
if hasattr(MailConfig, "MAIL_SERVER") and MailConfig.MAIL_SERVER is not None:
    application.config["MAIL_SERVER"] = MailConfig.MAIL_SERVER
if hasattr(MailConfig, "MAIL_PORT") and MailConfig.MAIL_PORT is not None:
    application.config["MAIL_PORT"] = MailConfig.MAIL_PORT
if hasattr(MailConfig, "MAIL_USE_TLS") and MailConfig.MAIL_USE_TLS is not None:
    application.config["MAIL_USE_TLS"] = MailConfig.MAIL_USE_TLS
if hasattr(MailConfig, "MAIL_USERNAME") and MailConfig.MAIL_USERNAME is not None:
    application.config["MAIL_USERNAME"] = MailConfig.MAIL_USERNAME
if hasattr(MailConfig, "MAIL_PASSWORD") and MailConfig.MAIL_PASSWORD is not None:
    application.config["MAIL_PASSWORD"] = MailConfig.MAIL_PASSWORD
if (
    hasattr(MailConfig, "MAIL_DEFAULT_SENDER")
    and MailConfig.MAIL_DEFAULT_SENDER is not None
):
    application.config["MAIL_DEFAULT_SENDER"] = MailConfig.MAIL_DEFAULT_SENDER

# --- Настройка логгера для __init__.py ---
if LOGGING_ENABLED:
    log_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs"
    )  # Папка logs внутри app/
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(
        log_dir, "__init__.py.log"
    )  # Отдельный файл для __init__.py

    # Отключаем распространение логов в консоль для всего пакета app и сервера werkzeug
    logging.getLogger("app").propagate = False

    w_logger = logging.getLogger("werkzeug")
    w_logger.propagate = False
    # Также можно установить уровень ERROR для werkzeug, чтобы совсем не видеть INFO/WARNING в терминале
    w_logger.setLevel(logging.ERROR)

    init_logger = logging.getLogger("app.__init__")  # Уникальное имя логгера
    init_logger.setLevel(logging.DEBUG)

    if not init_logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        init_logger.addHandler(file_handler)
    init_logger.info(f"Логгер для {__name__} настроен.")

    import sys

    init_logger.debug(f"DEBUG ENV: sys.executable = {sys.executable}")
    init_logger.debug(f"DEBUG ENV: sys.path = {sys.path}")
    init_logger.debug(
        f"DEBUG INIT: application.config после from_object(Config): {dict(application.config)}"
    )
# --- Конец настройки логгера ---

# Инициализация кеша с приложением
init_logger.debug("Инициализация Cache...")
cache.init_app(application)

# Инициализация Mail с приложением
init_logger.debug("Инициализация Mail...")
mail.init_app(application)
init_logger.debug("Инициализация CSRF...")
csrf.init_app(application)

# Настройка Flask-Login
init_logger.debug("Инициализация LoginManager...")
login_manager = LoginManager()
login_manager.init_app(application)
login_manager.login_view = "auth.login"
login_manager.login_message = (
    "Пожалуйста, войдите в систему для доступа к этой странице"
)


# Регистрация кастомного фильтра для форматирования даты
@application.template_filter("date")
def format_datetime(value, format="%Y-%m-%d %H:%M"):
    """Форматирует объект datetime в строку."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime(format)


@application.context_processor
def inject_current_year():
    """Передает текущий год во все шаблоны."""
    return {"current_year": datetime.now(timezone.utc).year}


# Импортируем и регистрируем Blueprints в конце файла, чтобы избежать циклических импортов
init_logger.debug("Начало импорта Blueprints...")
from .auth import auth_bp
from .blueprints.main_routes import main_routes
from .blueprints.parsing_routes import parsing_routes
from .blueprints.page_analyzer_routes import page_analyzer_routes
from .blueprints.ai_routes import ai_routes
from .blueprints.api_routes import api_routes
from .blueprints.top_sites_routes import top_sites_routes
from .blueprints.reports_routes import reports_bp
from .blueprints.project_routes import project_bp
from .positions_parsing.routes import positions_parsing_bp
from .text_tor.routes import text_tor_bp
from .redirect_checker.routes import redirect_checker_bp
from .clustering.clustering_routes import clustering_bp
from .blueprints.cluster_editor_routes import cluster_editor_bp
from .blueprints.settings_routes import settings_bp
from .http_status_checker.routes import http_status_checker_bp
from .blueprints.dashboard.dashboard_routes import dashboard_bp
from .blueprints.text_analyzer_routes import text_analyzer_routes
from .blueprints.seo_routes import seo_routes
from .uniqueness.routes import uniqueness_bp

application.register_blueprint(auth_bp, url_prefix="/auth")
application.register_blueprint(main_routes)
application.register_blueprint(parsing_routes)
application.register_blueprint(page_analyzer_routes)
application.register_blueprint(ai_routes)
application.register_blueprint(api_routes, url_prefix="/api")
application.register_blueprint(top_sites_routes)
application.register_blueprint(reports_bp, url_prefix="/api/reports")
application.register_blueprint(project_bp)
application.register_blueprint(positions_parsing_bp)
application.register_blueprint(text_tor_bp)
application.register_blueprint(redirect_checker_bp)
application.register_blueprint(clustering_bp)
application.register_blueprint(cluster_editor_bp)
application.register_blueprint(settings_bp)
application.register_blueprint(http_status_checker_bp)
application.register_blueprint(dashboard_bp)
application.register_blueprint(text_analyzer_routes)
application.register_blueprint(seo_routes)
application.register_blueprint(uniqueness_bp)
init_logger.debug("Blueprints успешно зарегистрированы")

from .db.database import init_db
from .db.settings_db import add_default_settings_if_not_exist

init_logger.debug("Попытка входа в app_context...")
with application.app_context():
    init_logger.debug("Внутри app_context. Инициализация БД...")
    init_db()
    add_default_settings_if_not_exist()


from . import models  # Убедимся, что модели загружены
