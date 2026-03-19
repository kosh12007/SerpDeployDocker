"""
Text converter routes blueprint for SERP bot application.
"""

from flask import Blueprint, render_template

text_converter_bp = Blueprint("text_converter", __name__)

@text_converter_bp.route("/text-converter")
def index():
    """Отображает страницу конвертера текста."""
    return render_template("text_converter.html")
