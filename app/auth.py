from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
import logging
import os
from .models import User
from app.db.settings_db import get_setting
from app.email import send_email
from app.db_config import LOGGING_ENABLED

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "auth.log")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Отключаем передачу логов в консоль
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    logger.info(f"Логгер для {__name__} настроен.")
# --- Конец настройки логгера ---

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    allow_registration = get_setting("ALLOW_REGISTRATION")
    if str(allow_registration).lower() != "true":
        logger.warning("Попытка регистрации при ALLOW_REGISTRATION=False")
        flash("Регистрация новых пользователей временно запрещена", "danger")
        return render_template("register.html")

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        logger.info(
            f"Попытка регистрации пользователя: username='{username}', email='{email}'"
        )

        if not username or not email or not password or not confirm_password:
            if LOGGING_ENABLED:
                logger.warning("Не все поля были заполнены при регистрации.")
            flash("Пожалуйста, заполните все поля", "danger")
            return render_template("register.html")

        if password != confirm_password:
            if LOGGING_ENABLED:
                logger.warning("Пароли не совпали при регистрации.")
            flash("Пароли не совпадают", "danger")
            return render_template("register.html")

        if len(password) < 8:
            if LOGGING_ENABLED:
                logger.warning("Попытка регистрации со слишком коротким паролем.")
            flash("Пароль должен содержать минимум 8 символов", "danger")
            return render_template("register.html")

        if User.get_by_username(username):
            if LOGGING_ENABLED:
                logger.warning(f"Пользователь с именем '{username}' уже существует.")
            flash("Пользователь с таким именем уже существует", "danger")
            return render_template("register.html")

        if User.get_by_email(email):
            if LOGGING_ENABLED:
                logger.warning(f"Пользователь с email '{email}' уже существует.")
            flash("Пользователь с такой почтой уже существует", "danger")
            return render_template("register.html")

        user = User.create(username, email, password)
        if user:
            login_user(user)
            if LOGGING_ENABLED:
                logger.info(
                    f"Пользователь '{username}' успешно зарегистрирован и вошел в систему."
                )
            flash("Регистрация успешна! Добро пожаловать!", "success")
            return redirect(url_for("main.index"))
        else:
            if LOGGING_ENABLED:
                logger.error(f"Ошибка при создании пользователя '{username}'.")
            flash("Ошибка при регистрации. Пожалуйста, попробуйте позже.", "danger")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        remember = request.form.get("remember") == "on"
        if LOGGING_ENABLED:
            logger.info(f"Попытка входа пользователя: username='{username}'")

        if not username or not password:
            if LOGGING_ENABLED:
                logger.warning("Не все поля были заполнены при входе.")
            flash("Пожалуйста, введите имя пользователя и пароль", "danger")
            return render_template("login.html")

        user = User.get_by_username(username)
        if user and user.check_password(password):
            if LOGGING_ENABLED:
                login_user(user, remember=remember)
            user.update_last_login()
            if LOGGING_ENABLED:
                logger.info(f"Пользователь '{username}' успешно вошел в систему.")
            flash("Вход выполнен успешно!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.index"))
        else:
            if LOGGING_ENABLED:
                logger.warning(
                    f"Неверные учетные данные для пользователя '{username}'."
                )
            flash("Неверное имя пользователя или пароль", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    if LOGGING_ENABLED:
        logger.info(f"Пользователь '{current_user.username}' вышел из системы.")
    logout_user()
    flash("Вы вышли из системы", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email")
        if LOGGING_ENABLED:
            logger.info(f"Запрос на сброс пароля для email: '{email}'")

        if not email:
            if LOGGING_ENABLED:
                logger.warning("Email не был указан при запросе на сброс пароля.")
            flash("Пожалуйста, введите email", "danger")
            return render_template("forgot-password.html")

        user = User.get_by_email(email)
        if user:
            token = user.generate_reset_token()
            if token:
                reset_url = url_for("auth.reset_password", token=token, _external=True)
                logger.info(
                    f"Сгенерирована ссылка для сброса пароля для пользователя '{user.username}'."
                )

                # Отправляем email с ссылкой для сброса
                send_email(
                    to=user.email,
                    subject="Сброс пароля",
                    template=render_template(
                        "email/reset_password.html", reset_url=reset_url
                    ),
                )

                flash("Инструкции по сбросу пароля отправлены на ваш email.", "info")
            else:
                if LOGGING_ENABLED:
                    logger.error(
                        f"Ошибка генерации токена сброса для пользователя '{user.username}'."
                    )
                flash(
                    "Ошибка генерации токена. Пожалуйста, попробуйте позже.", "danger"
                )
        else:
            if LOGGING_ENABLED:
                logger.info(
                    f"Пользователь с email '{email}' не найден, но отображено общее сообщение."
                )
            # В целях безопасности показываем одно и то же сообщение, даже если email не найден
            flash(
                "Если указанный email зарегистрирован, вы получите инструкции по сбросу пароля.",
                "info",
            )

    return render_template("forgot-password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    user = User.get_by_reset_token(token)
    if not user:
        if LOGGING_ENABLED:
            logger.warning(
                f"Использована недействительная или истекшая ссылка для сброса пароля. Токен: {token}"
            )
        flash("Недействительная или истекшая ссылка для сброса пароля", "danger")
        return redirect(url_for("auth.forgot_password"))

    if LOGGING_ENABLED:
        logger.info(
            f"Пользователь '{user.username}' перешел по ссылке для сброса пароля."
        )

    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not password or not confirm_password:
            flash("Пожалуйста, заполните все поля", "danger")
            return render_template("reset-password.html", token=token)

        if password != confirm_password:
            flash("Пароли не совпадают", "danger")
            return render_template("reset-password.html", token=token)

        if user.reset_password(password):
            if LOGGING_ENABLED:
                logger.info(
                    f"Пароль для пользователя '{user.username}' успешно изменен."
                )
            flash(
                "Пароль успешно изменен! Теперь вы можете войти с новым паролем.",
                "success",
            )
            return redirect(url_for("auth.login"))
        else:
            if LOGGING_ENABLED:
                logger.error(
                    f"Ошибка при сбросе пароля для пользователя '{user.username}'."
                )
            flash("Ошибка при сбросе пароля. Пожалуйста, попробуйте позже.", "danger")

    return render_template("reset-password.html", token=token)
