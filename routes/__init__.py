"""
Routes package — modular Flask Blueprints for Smart Money Terminal.
Keeps app.py lean by housing route handlers in focused modules.
"""

from .auth import auth_bp
from .watchlist import watchlist_bp
from .ai import ai_bp
from .news import news_bp


def register_blueprints(app):
    """Register all route blueprints with the Flask app."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(watchlist_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(news_bp)
