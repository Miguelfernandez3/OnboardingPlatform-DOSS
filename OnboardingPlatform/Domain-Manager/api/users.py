# api/users.py
"""
Endpoints related to user management (admin only).
"""
from flask import Blueprint, jsonify, request
from utils.error_handlers import handle_api_errors
from utils.app_context import get_dadm_instance
from utils.formatters import user_to_dict
from core.auth.decorators import require_admin
from core.auth.password_service import hash_password, validate_password_strength
from core.config import Config
from Database import DatabaseError
import logging
import math

users_bp = Blueprint('users', __name__)
config = Config()

@users_bp.route('/api/users', methods=['GET'])
@handle_api_errors
@require_admin
def get_users(current_user):
    """Lists users with pagination (admin only)"""
    # Obtener parámetros de paginación
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
    except ValueError:
        return jsonify({
            'error': 'Invalid pagination parameters',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    
    # Validar per_page máximo
    if per_page > 100:
        per_page = 100
    if per_page < 1:
        per_page = 20
    if page < 1:
        page = 1
    
    # Obtener filtros
    filters = {}
    role = request.args.get('role')
    if role:
        filters['role'] = role
    
    is_active = request.args.get('is_active')
    if is_active is not None:
        filters['is_active'] = is_active.lower() == 'true'
    
    search = request.args.get('search')
    if search:
        filters['search'] = search
    
    dadm = get_dadm_instance()
    if dadm is None:
        return jsonify({
            'error': 'DeviceDomainManager not initialized',
            'code': 'INITIALIZATION_ERROR',
            'details': {}
        }), 500
    
    try:
        # Obtener usuarios paginados (optimizado: 2 queries - count y results)
        users, total = dadm.db.getUsersPaginated(page=page, per_page=per_page, filters=filters)
        
        # Calcular información de paginación
        pages = math.ceil(total / per_page) if total > 0 else 0
        has_next = page < pages
        has_prev = page > 1
        
        # Convertir usuarios a dict
        users_list = [user_to_dict(user) for user in users]
        
        return jsonify({
            'users': users_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': pages,
                'has_next': has_next,
                'has_prev': has_prev
            }
        }), 200
    except DatabaseError as e:
        logging.error(f"Database error in get_users: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {}
        }), 500

@users_bp.route('/api/users', methods=['POST'])
@handle_api_errors
@require_admin
def create_user(current_user):
    """Creates a new user (admin only)"""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'error': 'Request body is required',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'user')
    
    if not email or not password:
        return jsonify({
            'error': 'Email and password are required',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    
    # Validar rol
    if role not in ['user', 'admin']:
        return jsonify({
            'error': 'Invalid role. Must be "user" or "admin"',
            'code': 'INVALID_ROLE',
            'details': {}
        }), 400
    
    # Validar formato de email básico
    if '@' not in email:
        return jsonify({
            'error': 'Invalid email format',
            'code': 'INVALID_EMAIL',
            'details': {}
        }), 400
    
    # Validar fortaleza del password
    is_valid, error_message = validate_password_strength(password, config.password_min_length)
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
        user = dadm.db.createUser(email, password, role=role)
        
        if user is None:
            return jsonify({
                'error': 'Email already exists',
                'code': 'EMAIL_EXISTS',
                'details': {}
            }), 409
        
        return jsonify({
            'user': user_to_dict(user)
        }), 201
    except DatabaseError as e:
        logging.error(f"Database error in create_user: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {}
        }), 500

@users_bp.route('/api/users/<int:user_id>', methods=['GET'])
@handle_api_errors
@require_admin
def get_user(current_user, user_id):
    """Gets a user by ID (admin only)"""
    dadm = get_dadm_instance()
    if dadm is None:
        return jsonify({
            'error': 'DeviceDomainManager not initialized',
            'code': 'INITIALIZATION_ERROR',
            'details': {}
        }), 500
    
    try:
        user = dadm.db.getUserById(user_id)
        if user is None:
            return jsonify({
                'error': f'User with id {user_id} not found',
                'code': 'USER_NOT_FOUND',
                'details': {}
            }), 404
        
        return jsonify({
            'user': user_to_dict(user)
        }), 200
    except DatabaseError as e:
        logging.error(f"Database error in get_user: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {}
        }), 500

@users_bp.route('/api/users/<int:user_id>/role', methods=['PUT'])
@handle_api_errors
@require_admin
def update_user_role(current_user, user_id):
    """Updates a user's role (admin only)"""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'error': 'Request body is required',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    
    new_role = data.get('role')
    
    if not new_role:
        return jsonify({
            'error': 'role is required',
            'code': 'INVALID_REQUEST',
            'details': {}
        }), 400
    
    # Validar rol
    if new_role not in ['user', 'admin']:
        return jsonify({
            'error': 'Invalid role. Must be "user" or "admin"',
            'code': 'INVALID_ROLE',
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
        # Verificar que el usuario existe
        user = dadm.db.getUserById(user_id)
        if user is None:
            return jsonify({
                'error': f'User with id {user_id} not found',
                'code': 'USER_NOT_FOUND',
                'details': {}
            }), 404
        
        # Actualizar rol
        success = dadm.db.updateUserRole(user_id, new_role)
        if success:
            updated_user = dadm.db.getUserById(user_id)
            return jsonify({
                'user': user_to_dict(updated_user)
            }), 200
        else:
            return jsonify({
                'error': 'Failed to update user role',
                'code': 'UPDATE_FAILED',
                'details': {}
            }), 500
    except DatabaseError as e:
        logging.error(f"Database error in update_user_role: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {}
        }), 500

@users_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@handle_api_errors
@require_admin
def delete_user(current_user, user_id):
    """Deletes a user (soft delete, admin only)"""
    dadm = get_dadm_instance()
    if dadm is None:
        return jsonify({
            'error': 'DeviceDomainManager not initialized',
            'code': 'INITIALIZATION_ERROR',
            'details': {}
        }), 500
    
    try:
        # Verificar que el usuario existe
        user = dadm.db.getUserById(user_id)
        if user is None:
            return jsonify({
                'error': f'User with id {user_id} not found',
                'code': 'USER_NOT_FOUND',
                'details': {}
            }), 404
        
        # No permitir auto-eliminación
        if user_id == current_user['id']:
            return jsonify({
                'error': 'Cannot delete your own account',
                'code': 'CANNOT_DELETE_SELF',
                'details': {}
            }), 400
        
        success = dadm.db.deleteUser(user_id)
        if success:
            return jsonify({}), 200
        else:
            return jsonify({
                'error': 'Failed to delete user',
                'code': 'DELETE_FAILED',
                'details': {}
            }), 500
    except DatabaseError as e:
        logging.error(f"Database error in delete_user: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {}
        }), 500

@users_bp.route('/api/users/<int:user_id>/activate', methods=['POST'])
@handle_api_errors
@require_admin
def activate_user(current_user, user_id):
    """Activates a user (admin only)"""
    dadm = get_dadm_instance()
    if dadm is None:
        return jsonify({
            'error': 'DeviceDomainManager not initialized',
            'code': 'INITIALIZATION_ERROR',
            'details': {}
        }), 500
    
    try:
        # Verificar que el usuario existe
        user = dadm.db.getUserById(user_id)
        if user is None:
            return jsonify({
                'error': f'User with id {user_id} not found',
                'code': 'USER_NOT_FOUND',
                'details': {}
            }), 404
        
        success = dadm.db.activateUser(user_id)
        if success:
            updated_user = dadm.db.getUserById(user_id)
            return jsonify({
                'user': user_to_dict(updated_user)
            }), 200
        else:
            return jsonify({
                'error': 'Failed to activate user',
                'code': 'ACTIVATE_FAILED',
                'details': {}
            }), 500
    except DatabaseError as e:
        logging.error(f"Database error in activate_user: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {}
        }), 500

@users_bp.route('/api/users/<int:user_id>/deactivate', methods=['POST'])
@handle_api_errors
@require_admin
def deactivate_user(current_user, user_id):
    """Deactivates a user (admin only)"""
    dadm = get_dadm_instance()
    if dadm is None:
        return jsonify({
            'error': 'DeviceDomainManager not initialized',
            'code': 'INITIALIZATION_ERROR',
            'details': {}
        }), 500
    
    try:
        # Verificar que el usuario existe
        user = dadm.db.getUserById(user_id)
        if user is None:
            return jsonify({
                'error': f'User with id {user_id} not found',
                'code': 'USER_NOT_FOUND',
                'details': {}
            }), 404
        
        # No permitir auto-desactivación
        if user_id == current_user['id']:
            return jsonify({
                'error': 'Cannot deactivate your own account',
                'code': 'CANNOT_DEACTIVATE_SELF',
                'details': {}
            }), 400
        
        success = dadm.db.deactivateUser(user_id)
        if success:
            updated_user = dadm.db.getUserById(user_id)
            return jsonify({
                'user': user_to_dict(updated_user)
            }), 200
        else:
            return jsonify({
                'error': 'Failed to deactivate user',
                'code': 'DEACTIVATE_FAILED',
                'details': {}
            }), 500
    except DatabaseError as e:
        logging.error(f"Database error in deactivate_user: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {}
        }), 500

