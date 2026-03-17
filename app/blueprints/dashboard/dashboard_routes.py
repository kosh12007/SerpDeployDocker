from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from ...services.dashboard_service import DashboardService

dashboard_bp = Blueprint(
    "dashboard", __name__, template_folder="../../../templates/dashboard"
)


@dashboard_bp.route("/api/dashboard/stats")
@login_required
def get_dashboard_stats():
    """
    API endpoint для получения статистики дашборда.

    Параметры:
    - project_id: ID проекта (опционально, 'all' для всех проектов)
    - variant_id: ID варианта парсинга (опционально)
    - date_from: Базовая дата для сравнения (с чем сравниваем), формат 'YYYY-MM-DD'
    - date_to: Целевая дата (что сравниваем), формат 'YYYY-MM-DD'

    Если указаны обе даты - рассчитывается разница между ними.
    Если указана только date_to - показывается статистика за эту дату без разницы.
    Если даты не указаны - показывается последняя статистика.
    """
    project_id = request.args.get("project_id")
    variant_id = request.args.get("variant_id", type=int)
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    if project_id == "all":
        project_id = None

    stats = DashboardService.get_stats(
        current_user.id,
        project_id,
        variant_id=variant_id,
        date_from=date_from,
        date_to=date_to,
    )
    # Добавляем данные о балансе и лимитах из профиля пользователя
    stats["limits"] = current_user.limits
    return jsonify(stats)


@dashboard_bp.route("/api/dashboard/projects")
@login_required
def get_projects_list():
    """API endpoint для получения списка проектов пользователя."""
    projects = DashboardService.get_user_projects(current_user.id)
    return jsonify(projects)


@dashboard_bp.route("/api/dashboard/activity")
@login_required
def get_dashboard_activity():
    """API endpoint для получения последних действий."""
    activity = DashboardService.get_recent_activity(current_user.id)
    return jsonify(activity)


@dashboard_bp.route("/api/dashboard/uniqueness-stats")
@login_required
def get_uniqueness_stats():
    """API endpoint для получения расширенной аналитики уникальности (только для суперадминов)."""
    if not getattr(current_user, "is_super_admin", False):
        return jsonify({"error": "Forbidden"}), 403

    from ...db.uniqueness_db import get_uniqueness_analytics
    from ...db.settings_db import get_setting

    # Получаем TTL из настроек (по умолчанию 14 дней)
    ttl_days = int(get_setting("UNIQUENESS_CACHE_TTL") or 14)

    stats = get_uniqueness_analytics(ttl_days=ttl_days)
    return jsonify(stats)
