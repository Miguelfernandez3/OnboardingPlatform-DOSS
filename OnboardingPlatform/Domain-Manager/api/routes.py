# api/routes.py
"""
Registration of all API blueprints.
"""
from flask import Blueprint
from api import devices, policies, threats, mitigations, auth, users, enforcement_admin, me_notifications, me_settings, telegram_webhook, service_logs

def register_blueprints(app):
    """
    Registers all blueprints in the Flask application.
    
    Args:
        app: Flask instance
    """
    # Register blueprints
    app.register_blueprint(devices.devices_bp)
    app.register_blueprint(policies.policies_bp)
    app.register_blueprint(threats.threats_bp)
    app.register_blueprint(mitigations.mitigations_bp)
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(users.users_bp)
    app.register_blueprint(enforcement_admin.enforcement_admin_bp)
    app.register_blueprint(me_settings.me_settings_bp)
    app.register_blueprint(me_notifications.me_notifications_bp)
    app.register_blueprint(telegram_webhook.telegram_webhook_bp)
    app.register_blueprint(service_logs.service_logs_bp)
