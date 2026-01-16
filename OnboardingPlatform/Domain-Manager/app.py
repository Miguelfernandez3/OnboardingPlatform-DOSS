# app.py
"""
Main Flask application entry point.
Initializes Flask app and DeviceDomainManager instance.
"""
import logging
import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from core.device_domain_manager import DeviceDomainManager
from api.routes import register_blueprints
from utils.app_context import set_dadm_instance

# Load environment variables from .env file
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Configure CORS
CORS(app)

# Global DeviceDomainManager instance
dadm = None

if __name__ == '__main__':
    # Configure logging with more detailed level for debugging
    logging.basicConfig(
        level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Log to console
            logging.FileHandler('DeviceDomainManager.log')  # Also log to file
        ]
    )
    
    logging.info("=" * 80)
    logging.info("Starting Device and Domain manager")
    logging.info("=" * 80)
    
    try:
        logging.debug("Creating DeviceDomainManager instance")
        dadm = DeviceDomainManager()
        logging.info("DeviceDomainManager instance created successfully")
        
        # Set global instance for error handlers
        set_dadm_instance(dadm)
        
        # Create admin user if it doesn't exist
        try:
            from scripts.create_admin import create_admin
            logging.info("Checking for admin user...")
            create_admin()
        except Exception as e:
            logging.warning(f"Could not create admin user: {e}. Continuing anyway...")
        
        # Register all blueprints
        register_blueprints(app)
        
        logging.info("Starting Flask application on port 4321")
        app.run(host='0.0.0.0', use_reloader=False, debug=True, port=4321)
    except Exception as e:
        logging.critical(f"Fatal error starting DeviceDomainManager: {e}", exc_info=True)
        raise

