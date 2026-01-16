# api/auth.py
"""
Endpoints related to authentication.
"""
from flask import Blueprint, jsonify, request
from utils.error_handlers import handle_api_errors
from utils.app_context import get_dadm_instance
from utils.formatters import user_to_dict
from core.auth.password_service import hash_password, verify_password, validate_password_strength
from core.auth.jwt_service import generate_access_token, generate_refresh_token, verify_token
from core.auth.decorators import require_auth
from core.auth.exceptions import InvalidCredentialsError
from core.config import Config
from Database import DatabaseError
from datetime import datetime, timezone
import logging

auth_bp = Blueprint('auth', __name__)
config = Config()

@auth_bp.route('/api/auth/login', methods=['POST'])
@handle_api_errors
def login():
    """Logs in a user and returns JWT tokens (public endpoint)"""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'error': 'Request body is required',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({
            'error': 'Email and password are required',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    
    dadm = get_dadm_instance()
    if dadm is None:
        return jsonify({
            'error': 'DeviceDomainManager not initialized',
            'code': 'INITIALIZATION_ERROR',
            'details': {}
        }), 500
    
    try:
        # Buscar usuario
        user = dadm.db.getUser(email)
        
        if user is None:
            return jsonify({
                'error': 'Invalid email or password',
                'code': 'INVALID_CREDENTIALS',
                'details': {}
            }), 401
        
        # Verificar password
        if not dadm.db.verifyPassword(user, password):
            return jsonify({
                'error': 'Invalid email or password',
                'code': 'INVALID_CREDENTIALS',
                'details': {}
            }), 401
        
        # Verificar que el usuario esté activo
        if not user.is_active:
            return jsonify({
                'error': 'User account is inactive',
                'code': 'USER_INACTIVE',
                'details': {}
            }), 401
        
        # Actualizar último login
        dadm.db.updateUserLastLogin(user.id)
        
        # Generar tokens
        access_token = generate_access_token(user.id, user.email, user.role)
        refresh_token = generate_refresh_token(user.id, user.email, user.role)
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role
            }
        }), 200
    except DatabaseError as e:
        logging.error(f"Database error in login: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {}
        }), 500

@auth_bp.route('/api/auth/refresh', methods=['POST'])
@handle_api_errors
def refresh():
    """Refreshes an access token using a refresh token"""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'error': 'Request body is required',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    
    refresh_token = data.get('refresh_token')
    
    if not refresh_token:
        return jsonify({
            'error': 'refresh_token is required',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    
    try:
        # Verificar refresh token
        payload = verify_token(refresh_token)
        
        # Verificar que sea un refresh token
        if payload.get('type') != 'refresh':
            return jsonify({
                'error': 'Invalid token type',
                'code': 'INVALID_TOKEN_TYPE',
                'details': {}
            }), 401
        
        dadm = get_dadm_instance()
        if dadm is None:
            return jsonify({
                'error': 'DeviceDomainManager not initialized',
                'code': 'INITIALIZATION_ERROR',
                'details': {}
            }), 500
        
        # Verificar que el usuario existe y está activo
        user = dadm.db.getUserById(payload['user_id'])
        if user is None:
            return jsonify({
                'error': 'User not found',
                'code': 'USER_NOT_FOUND',
                'details': {}
            }), 401
        
        if not user.is_active:
            return jsonify({
                'error': 'User account is inactive',
                'code': 'USER_INACTIVE',
                'details': {}
            }), 401
        
        # Generar nuevo access token
        access_token = generate_access_token(user.id, user.email, user.role)
        
        return jsonify({
            'access_token': access_token
        }), 200
    except Exception as e:
        logging.error(f"Error in refresh: {e}", exc_info=True)
        return jsonify({
            'error': 'Invalid or expired refresh token',
            'code': 'INVALID_REFRESH_TOKEN',
            'details': {}
        }), 401

@auth_bp.route('/api/auth/me', methods=['GET'])
@handle_api_errors
@require_auth
def get_current_user(current_user):
    """Gets information about the current authenticated user"""
    dadm = get_dadm_instance()
    if dadm is None:
        return jsonify({
            'error': 'DeviceDomainManager not initialized',
            'code': 'INITIALIZATION_ERROR',
            'details': {}
        }), 500
    
    try:
        user = dadm.db.getUserById(current_user['id'])
        if user is None:
            return jsonify({
                'error': 'User not found',
                'code': 'USER_NOT_FOUND',
                'details': {}
            }), 404
        
        return jsonify({
            'user': user_to_dict(user)
        }), 200
    except DatabaseError as e:
        logging.error(f"Database error in get_current_user: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {}
        }), 500

@auth_bp.route('/api/auth/change-password', methods=['PUT'])
@handle_api_errors
@require_auth
def change_password(current_user):
    """Changes the password of the current authenticated user"""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'error': 'Request body is required',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({
            'error': 'current_password and new_password are required',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    
    # Validar fortaleza del nuevo password
    is_valid, error_message = validate_password_strength(new_password, config.password_min_length)
    if not is_valid:
        return jsonify({
            'error': error_message,
            'code': 'WEAK_PASSWORD',
            'details': {}
        }), 400
    
    dadm = get_dadm_instance()
    if dadm is None:
        return jsonify({
            'error': 'DeviceDomainManager not initialized',
            'code': 'INITIALIZATION_ERROR',
            'details': {}
        }), 500
    
    try:
        user = dadm.db.getUserById(current_user['id'])
        if user is None:
            return jsonify({
                'error': 'User not found',
                'code': 'USER_NOT_FOUND',
                'details': {}
            }), 404
        
        # Verificar password actual
        if not dadm.db.verifyPassword(user, current_password):
            return jsonify({
                'error': 'Current password is incorrect',
                'code': 'INVALID_PASSWORD',
                'details': {}
            }), 401
        
        # Actualizar password
        new_password_hash = hash_password(new_password)
        user.password_hash = new_password_hash
        user.updated_at = datetime.now(timezone.utc)
        dadm.db.session.commit()
        
        return jsonify({
            'message': 'Password changed successfully'
        }), 200
    except DatabaseError as e:
        logging.error(f"Database error in change_password: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {}
        }), 500
    except Exception as e:
        logging.error(f"Error in change_password: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to change password',
            'code': 'PASSWORD_CHANGE_FAILED',
            'details': {}
        }), 500
