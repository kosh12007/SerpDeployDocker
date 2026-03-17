import json
import os
from datetime import datetime, timezone
from flask import url_for, current_app


class SitemapService:
    @staticmethod
    def get_sitemap_path():
        """Возвращает путь к файлу sitemap.json."""
        return os.path.join(current_app.root_path, "static", "sitemap.json")

    @staticmethod
    def get_template_path():
        """Возвращает путь к шаблону sitemap.xml."""
        return os.path.join(current_app.root_path, "templates", "sitemap.xml")

    @classmethod
    def ensure_template_exists(cls):
        """Проверяет наличие шаблона sitemap.xml и создает его, если он отсутствует."""
        path = cls.get_template_path()
        if not os.path.exists(path):
            current_app.logger.info(f"Шаблон {path} не найден. Создаю базовый шаблон.")
            content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    {% if entries %}
        {% for entry in entries %}
        <url>
            <loc>{{ entry.loc }}</loc>
            <lastmod>{{ entry.lastmod }}</lastmod>
            <changefreq>{{ entry.changefreq }}</changefreq>
            <priority>{{ entry.priority }}</priority>
        </url>
        {% endfor %}
    {% else %}
        <url>
            <loc>{{ url_for('main.index', _external=True) }}</loc>
            <lastmod>{{ lastmod }}</lastmod>
            <changefreq>daily</changefreq>
            <priority>1.0</priority>
        </url>
    {% endif %}
</urlset>
"""
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return True
            except Exception as e:
                current_app.logger.error(f"Не удалось создать шаблон sitemap.xml: {e}")
        return False

    @classmethod
    def load_sitemap(cls):
        """Загружает данные sitemap из JSON файла."""
        path = cls.get_sitemap_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                current_app.logger.error(f"Ошибка при загрузке sitemap.json: {e}")
        return []

    @classmethod
    def save_sitemap(cls, data):
        """Сохраняет данные sitemap в JSON файл."""
        path = cls.get_sitemap_path()
        try:
            # Обеспечиваем существование папки static
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            current_app.logger.error(f"Ошибка при сохранении sitemap.json: {e}")
            return False

    @classmethod
    def generate_base_sitemap(cls):
        """Генерирует базовый список публичных роутов."""
        routes = [
            {"url": "/", "priority": "1.0", "changefreq": "daily"},
            {"url": "/auth/login", "priority": "0.8", "changefreq": "monthly"},
            {"url": "/auth/register", "priority": "0.8", "changefreq": "monthly"},
            {
                "url": "/auth/forgot-password",
                "priority": "0.5",
                "changefreq": "monthly",
            },
            # Добавьте другие публичные роуты, если они есть
        ]

        lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for route in routes:
            route["lastmod"] = lastmod

        return routes

    @classmethod
    def get_xml_data(cls):
        """Превращает JSON данные в формат, пригодный для шаблона sitemap.xml."""
        entries = cls.load_sitemap()
        if not entries:
            # Если файла нет, возвращаем пустой список или генерируем на лету
            return []

        # Формируем полные URL
        processed = []
        for entry in entries:
            # Пытаемся обработать как относительный путь или именованный роут
            url = entry.get("url", "/")
            processed.append(
                {
                    "loc": (
                        url
                        if url.startswith("http")
                        else url_for("main.index", _external=True).rstrip("/") + url
                    ),
                    "lastmod": entry.get("lastmod"),
                    "changefreq": entry.get("changefreq", "monthly"),
                    "priority": entry.get("priority", "0.5"),
                }
            )
        return processed

    @staticmethod
    def get_robots_path():
        """Возвращает путь к шаблону robots.txt."""
        path = os.path.join(current_app.root_path, "..", "templates", "robots.txt")
        current_app.logger.debug(f"DEBUG: Путь к robots.txt: {path}")
        return path

    @classmethod
    def load_robots_txt(cls):
        """Загружает содержимое robots.txt."""
        path = cls.get_robots_path()
        current_app.logger.debug(f"DEBUG: Попытка загрузки robots.txt из: {path}")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    current_app.logger.debug(
                        f"DEBUG: robots.txt успешно прочитан, длина: {len(content)}"
                    )
                    return content
            except Exception as e:
                current_app.logger.error(f"DEBUG: Ошибка при чтении robots.txt: {e}")
        else:
            current_app.logger.warning(
                f"DEBUG: Файл robots.txt не найден по пути: {path}"
            )
        return ""

    @classmethod
    def save_robots_txt(cls, content):
        """Сохраняет содержимое robots.txt."""
        path = cls.get_robots_path()
        current_app.logger.debug(f"DEBUG: Попытка сохранения robots.txt в: {path}")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            current_app.logger.info(f"DEBUG: robots.txt успешно сохранен в: {path}")
            return True
        except Exception as e:
            current_app.logger.error(f"DEBUG: Ошибка при сохранении robots.txt: {e}")
            return False
