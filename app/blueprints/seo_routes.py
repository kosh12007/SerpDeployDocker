from flask import Blueprint, render_template, make_response
from app.services.sitemap_service import SitemapService
from datetime import datetime, timezone

seo_routes = Blueprint("seo", __name__)


@seo_routes.route("/robots.txt")
def robots():
    """Служит robots.txt напрямую с диска, чтобы избежать кеширования шаблонов."""
    content = SitemapService.load_robots_txt()
    response = make_response(content)
    response.headers["Content-Type"] = "text/plain"
    # Добавляем заголовки для предотвращения кеширования
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@seo_routes.route("/sitemap.xml")
def sitemap():
    """Генерирует sitemap.xml из сохраненных данных."""
    SitemapService.ensure_template_exists()
    entries = SitemapService.get_xml_data()

    # Резервный вариант, если список пуст
    if not entries:
        lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        content = render_template("sitemap.xml", lastmod=lastmod)
    else:
        content = render_template("sitemap.xml", entries=entries)

    response = make_response(content)
    response.headers["Content-Type"] = "application/xml"
    # Добавляем заголовки для предотвращения кеширования
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
