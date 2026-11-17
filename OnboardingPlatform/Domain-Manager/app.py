# app.py
"""
Main Flask application entry point.
Initializes Flask app and DeviceDomainManager instance.
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler
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


def _env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}

if __name__ == '__main__':
    # Configure logging early and force override in case any module already created handlers.
    log_level_name = os.getenv('LOG_LEVEL', 'DEBUG').upper()
    log_level = getattr(logging, log_level_name, logging.DEBUG)
    server_port = int(os.getenv('DADM_PORT', '4321'))
    debug_enabled = _env_flag('FLASK_DEBUG', default=False)
    file_handler = TimedRotatingFileHandler(
        filename='DeviceDomainManager.log',
        when='midnight',
        interval=1,
        backupCount=2,
        utc=True,
    )

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Log to console
            file_handler,  # Rotated file logs with retention
        ],
        force=True,
    )
    
    logging.getLogger('dicttoxml').setLevel(logging.WARNING)
    logging.info("=" * 80)
    logging.info("Starting Device and Domain manager")
    logging.info("=" * 80)
    
    try:
        logging.debug("Creating DeviceDomainManager instance")
        dadm = DeviceDomainManager()
        logging.info("DeviceDomainManager instance created successfully")
        logging.info("Domain-Manager database location: %s", dadm.db.database_location)
        
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
        
        logging.info("Starting Flask application on port %s (debug=%s)", server_port, debug_enabled)
        app.run(host='0.0.0.0', use_reloader=False, debug=debug_enabled, port=server_port)
    except Exception as e:
        logging.critical(f"Fatal error starting DeviceDomainManager: {e}", exc_info=True)
        raise
