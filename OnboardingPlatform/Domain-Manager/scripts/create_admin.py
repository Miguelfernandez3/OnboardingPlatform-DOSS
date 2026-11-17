# scripts/create_admin.py
"""
Script to create the initial admin user (as superadmin).
Can be run manually or called during application startup.
Automatically executed when the application starts.
The initial user is created with role 'superadmin' so it cannot be deactivated or deleted.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from Database import Database
from core.auth.password_service import hash_password

def create_admin():
    """
    Creates the initial admin user as superadmin if it doesn't exist.
    Uses environment variables ADMIN_EMAIL and ADMIN_PASSWORD.
    The user is created with role 'superadmin' (cannot be deactivated or deleted).
    """
    # Get admin credentials from environment variables
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@doss.local')
    admin_password = os.getenv('ADMIN_PASSWORD')
    
    if not admin_password:
        logging.error("ADMIN_PASSWORD environment variable is required")
        print("ERROR: ADMIN_PASSWORD environment variable is required")
        return False
    
    try:
        db = Database()
        
        # Check if admin already exists
        existing_user = db.getUser(admin_email)
        if existing_user:
            if existing_user.role == 'superadmin':
                logging.info(f"Superadmin user {admin_email} already exists")
                print(f"Superadmin user {admin_email} already exists")
                return True
            # Upgrade existing user to superadmin (initial user protection)
            logging.info(f"Upgrading user {admin_email} to superadmin role")
            db.updateUserRole(existing_user.id, 'superadmin')
            print(f"Updated user {admin_email} to superadmin role")
            return True
        
        # Create new user as superadmin
        user = db.createUser(admin_email, admin_password, role='superadmin')
        if user:
            logging.info(f"Superadmin user {admin_email} created successfully")
            print(f"Superadmin user {admin_email} created successfully")
            return True
        else:
            logging.error(f"Failed to create superadmin user {admin_email}")
            print(f"ERROR: Failed to create superadmin user {admin_email}")
            return False
    except Exception as e:
        logging.error(f"Error creating admin user: {e}", exc_info=True)
        print(f"ERROR: {e}")
        return False

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    create_admin()
