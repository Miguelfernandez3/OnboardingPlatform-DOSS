# scripts/create_admin.py
"""
Script to create the initial admin user.
Can be run manually or called during application startup.
Automatically executed when the application starts.
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
    Creates an admin user if it doesn't exist.
    Uses environment variables ADMIN_EMAIL and ADMIN_PASSWORD.
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
            if existing_user.role == 'admin':
                logging.info(f"Admin user {admin_email} already exists")
                print(f"Admin user {admin_email} already exists")
                return True
            else:
                # Update existing user to admin
                logging.info(f"Updating user {admin_email} to admin role")
                db.updateUserRole(existing_user.id, 'admin')
                print(f"Updated user {admin_email} to admin role")
                return True
        
        # Create new admin user
        user = db.createUser(admin_email, admin_password, role='admin')
        if user:
            logging.info(f"Admin user {admin_email} created successfully")
            print(f"Admin user {admin_email} created successfully")
            return True
        else:
            logging.error(f"Failed to create admin user {admin_email}")
            print(f"ERROR: Failed to create admin user {admin_email}")
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
