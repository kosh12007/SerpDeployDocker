from flask import current_app
from flask_mail import Message
from app import mail
import logging
import os
from app.db_config import LOGGING_ENABLED
from app.config import MailConfig  # Импортируем MailConfig

# --- Настройка логгера ---
if LOGGING_ENABLED:
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "email.log")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Отключаем передачу логов вышестоящим логгерам (консоли)
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


def send_email(to, subject, template):
    """
    Отправляет электронное письмо.

    :param to: Адрес получателя.
    :param subject: Тема письма.
    :param template: HTML-содержимое письма.
    """
    try:
        # Получаем настройки напрямую из MailConfig
        server = MailConfig.MAIL_SERVER
        port = MailConfig.MAIL_PORT
        use_tls = MailConfig.MAIL_USE_TLS
        username = MailConfig.MAIL_USERNAME
        password = MailConfig.MAIL_PASSWORD
        sender_from_config = MailConfig.MAIL_DEFAULT_SENDER

        # Логируем настройки, которые будут использованы Flask-Mail
        if LOGGING_ENABLED:
            logger.debug(
                f"SMTP Настройки Flask-Mail (из MailConfig): SERVER={server}, "
                f"PORT={port}, USE_TLS={use_tls}, "
                f"USERNAME={username}, SENDER={sender_from_config}"
            )

        # Используем настройки из MailConfig для создания сообщения
        # sender для Message может быть передан из sender_from_config
        msg = Message(
            subject,
            recipients=[to],
            html=template,
            sender=sender_from_config,  # Используем значение из MailConfig
        )
        mail.send(msg)
        if LOGGING_ENABLED:
            logger.info(f"Письмо успешно отправлено на адрес {to}")
    except Exception as e:
        if LOGGING_ENABLED:
            logger.error(f"Ошибка при отправке письма на адрес {to}: {e}")
