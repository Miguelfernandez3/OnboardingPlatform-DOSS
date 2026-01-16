# api/routes.py
"""
Registration of all API blueprints.
"""
from flask import Blueprint
from api import devices, policies, threats, mitigations, auth, users

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

