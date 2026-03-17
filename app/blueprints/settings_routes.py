from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
import os
from app.db.database import (
    execute_sql_from_file,
    get_applied_migrations,
    mark_migration_as_applied,
)
from app.db.settings_db import get_all_settings, update_setting
from app.services.sitemap_service import SitemapService

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
def settings_page():
    if not current_user.is_admin:
        flash("У вас нет доступа к этой странице.", "danger")
        return redirect(url_for("main_routes.index"))

    if request.method == "POST":
        if not current_user.is_super_admin:
            flash("У вас нет прав для изменения настроек.", "danger")
            return redirect(url_for(".settings_page"))

        for key, value in request.form.items():
            update_setting(key, value)
        flash("Настройки успешно обновлены.", "success")
        return redirect(url_for(".settings_page"))

    settings = get_all_settings()
    return render_template("settings.html", settings=settings)


@settings_bp.route("/migrate", methods=["POST"])
@login_required
def migrate_database():
    # Проверка, что пользователь является суперадминистратором
    if not current_user.is_super_admin:
        flash("У вас нет прав для выполнения этой операции.", "danger")
        return redirect(url_for(".settings_page"))

    migrations_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "migrations"
    )
    try:
        # Получаем все .sql файлы из папки миграций и сортируем их
        all_migration_files = sorted(
            [f for f in os.listdir(migrations_dir) if f.endswith(".sql")]
        )

        # Получаем список уже примененных миграций из БД
        applied_migrations = get_applied_migrations()

        # Определяем, какие миграции еще не были применены
        pending_migrations = [
            f for f in all_migration_files if f not in applied_migrations
        ]

        if not pending_migrations:
            flash("Нет новых миграций для применения.", "info")
            return redirect(url_for(".settings_page"))

        for file in pending_migrations:
            filepath = os.path.join(migrations_dir, file)
            success, message = execute_sql_from_file(filepath)

            if success:
                # Если миграция успешна, записываем ее в таблицу migrations
                mark_migration_as_applied(file)
                flash(f"Миграция {file} успешно применена.", "success")
            else:
                flash(f"Ошибка при применении миграции {file}: {message}", "danger")
                # Прерываем процесс, если одна из миграций не удалась
                break
    except Exception as e:
        flash(f"Произошла ошибка при выполнении миграций: {e}", "danger")

    return redirect(url_for("settings.settings_page"))


@settings_bp.route("/sitemap", methods=["GET"])
@login_required
def get_sitemap():
    if not current_user.is_admin:
        return {"error": "Unauthorized"}, 403
    return {"sitemap": SitemapService.load_sitemap()}


@settings_bp.route("/sitemap", methods=["POST"])
@login_required
def save_sitemap():
    if not current_user.is_super_admin:
        return {"error": "Unauthorized"}, 403

    data = request.json.get("sitemap", [])
    if SitemapService.save_sitemap(data):
        return {"status": "success"}
    return {"status": "error", "message": "Failed to save sitemap"}


@settings_bp.route("/sitemap/generate", methods=["POST"])
@login_required
def generate_sitemap():
    if not current_user.is_super_admin:
        return {"error": "Unauthorized"}, 403

    base_sitemap = SitemapService.generate_base_sitemap()
    return {"sitemap": base_sitemap}


@settings_bp.route("/robots", methods=["GET"])
@login_required
def get_robots():
    if not current_user.is_admin:
        return {"error": "Unauthorized"}, 403
    from flask import current_app

    current_app.logger.debug("DEBUG: Вызов get_robots API")
    content = SitemapService.load_robots_txt()
    return {"content": content, "status": "success"}


@settings_bp.route("/robots", methods=["POST"])
@login_required
def save_robots():
    if not current_user.is_super_admin:
        return {"error": "Unauthorized"}, 403

    from flask import current_app

    current_app.logger.debug("DEBUG: Вызов save_robots API")
    content = request.json.get("content", "")
    current_app.logger.debug(
        f"DEBUG: Получен контент для сохранения, длина: {len(content)}"
    )
    if SitemapService.save_robots_txt(content):
        return {"status": "success"}
    return {"status": "error", "message": "Failed to save robots.txt"}
