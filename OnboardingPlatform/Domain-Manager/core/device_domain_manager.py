# core/device_domain_manager.py
"""
Refactored main DeviceDomainManager class.
Consolidates all business logic while maintaining compatibility with the original code.
"""
import logging
import Database
import ERADriver
import os
import sys
from typing import Optional
import json

# Conditional import of confluent_kafka
try:
    from confluent_kafka import Consumer, Producer
    KAFKA_AVAILABLE = True
    logging.debug("confluent_kafka imported successfully")
except ImportError as e:
    KAFKA_AVAILABLE = False
    Consumer = None
    Producer = None
    logging.warning(f"confluent_kafka not available: {e}. Kafka functionality will be disabled.")
except Exception as e:
    KAFKA_AVAILABLE = False
    Consumer = None
    Producer = None
    logging.error(f"Error importing confluent_kafka: {e}. Kafka functionality will be disabled.", exc_info=True)

# Configure path for Policy_Translator
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(parent_dir)

from Policy_Translator import mudtranslator
from lxml import etree
from datetime import datetime, timezone

# Import services and clients
from core.config import Config
from clients.mud_manager_client import MUDManagerClient
from clients.threat_mud_client import ThreatMUDClient
from clients.feam_client import FEAMClient
from services.mud_service import MUDService
from services.threat_service import ThreatService
from services.feam_service import FEAMService
from services.device_service import DeviceService
from services.policy_service import PolicyService
from services.policy_enforcement_service import PolicyEnforcementService
from services.mitigation_service import MitigationService
from services.log_retention_service import LogRetentionService
from utils.xml_parser import parse_mitigations_tmud, parse_mitigations_mud

class DeviceDomainManager:
    """
    Main class for managing devices and domains.
    Refactored version that maintains all original functionality.
    """
    
    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initializes the DeviceDomainManager.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = Config(config_path)
        
        # Initialize database
        self.db = Database.Database()
        
        # Initialize HTTP clients
        self.mud_manager_client = MUDManagerClient(
            base_url=self.config.mud_manager_url,
            timeout=10
        )
        self.threat_mud_client = ThreatMUDClient(
            base_url=self.config.threat_mud_manager_url,
            timeout=5
        )
        self.feam_client = FEAMClient(
            base_url=self.config.feam_server,
            session_id=self.config.feam_session_id,
            timeout=5
        )
        
        # Initialize services
        self.mud_service = MUDService(self.mud_manager_client)
        self.threat_service = ThreatService(self.threat_mud_client, self.db)
        self.feam_service = FEAMService(self.feam_client, self.db)
        self.device_service = DeviceService(
            self.db,
            self.mud_service,
            self.feam_service
        )
        self.policy_enforcement_service = PolicyEnforcementService(
            self.db,
            self.reconfigureDevice
        )
        self.policy_service = PolicyService(
            self.db,
            self.policy_enforcement_service
        )
        self.device_service.set_policy_services(
            self.policy_service,
            self.policy_enforcement_service
        )
        self.device_service.configure_polling(
            poll_interval_seconds=self.config.dsp_threat_poll_interval_seconds,
            db_factory=self.db.__class__,
        )
        self.log_retention_service = LogRetentionService(
            self.db,
            db_factory=self.db.__class__,
        )
        self.log_retention_service.configure(
            retention_days=self.config.log_retention_days,
            interval_seconds=self.config.log_retention_interval_seconds,
            vacuum_enabled=self.config.log_retention_vacuum_enabled,
            vacuum_interval_seconds=self.config.log_retention_vacuum_interval_seconds,
        )
        self.mitigation_service = MitigationService(
            self.db,
            self.threat_service,
            self.policy_enforcement_service
        )
        self.device_service.set_mitigation_service(self.mitigation_service)

        # Initialize FEAM
        self.feam_service.prepare()
        logging.info(
            "Polling configurado al inicio: FEAM_SYNC_POLL_INTERVAL_SECONDS=%ss, DSP_THREAT_POLL_INTERVAL_SECONDS=%ss",
            self.config.feam_sync_poll_interval_seconds,
            self.config.dsp_threat_poll_interval_seconds,
        )
        self.feam_service.start_sync_jobs(self.config.feam_sync_poll_interval_seconds)
        self.device_service.start_dsp_threat_polling()
        self.log_retention_service.start_retention_jobs()
        
        # Kafka (maintain compatibility with original code)
        self.broker = self.config.broker
        self.topics = self.config.topics
        self.consumer = None
        
        # Store original URLs for compatibility
        self.FEAM_server = self.config.feam_server
        self.FEAM_sessionId = self.config.feam_session_id
        self.ThreatMUDManager_url = self.config.threat_mud_manager_url
        self.MUDManager_url = self.config.mud_manager_url
        
        # Kafka producer initialization (disabled - uncomment if Kafka is available and needed)
        # if KAFKA_AVAILABLE:
        #     try:
        #         pconf = {
        #             'bootstrap.servers': self.broker,
        #         }
        #         self.producer = Producer(pconf)
        #         logging.info(f"Kafka producer initialized for broker {self.broker}")
        #     except Exception as e:
        #         logging.warning(f"Could not initialize Kafka producer: {e}")
        #         self.producer = None
        # else:
        #     self.producer = None
    
    # ==================== COMPATIBILITY METHODS ====================
    # These methods maintain the original interface for compatibility
    
    def prepareFEAM(self):
        """Compatibility: redirects to feam_service.prepare()"""
        self.feam_service.prepare()
    
    def FEAMcheckPIN(self, pin=1234):
        """Compatibility: redirects to feam_service.check_pin()"""
        return self.feam_service.check_pin(pin)
    
    def FEAMgetGendspFromIdspId(self, idsp_id):
        """Compatibility: redirects to feam_service.get_gendsp_from_idsp_id()"""
        return self.feam_service.get_gendsp_from_idsp_id(idsp_id)
    
    def configBroker(self):
        """Configures the Kafka broker (only if Kafka is available)"""
        if not KAFKA_AVAILABLE or Consumer is None:
            logging.warning("Kafka is not available. Cannot configure broker.")
            self.consumer = None
            return
        
        try:
            conf = {
                'bootstrap.servers': self.broker,
                'group.id': 'DomainDeviceManager'
            }
            
            # Create Consumer instance
            self.consumer = Consumer(conf)
            logging.info(f"Kafka consumer initialized for broker {self.broker}")
        except Exception as e:
            logging.error(f"Error initializing Kafka consumer: {e}", exc_info=True)
            self.consumer = None
    
    def reconfigureDevice(self, mitigation_data, device):
        """Reconfigures a device using ERADriver."""
        message = ERADriver.compose_message_change_signature()
        logging.info(f"Sending reconfiguration for device {device.identifier}. Reconfiguration message: {message}")
        ERADriver.send_message(device.ip, message, edk=device.edk)
    
    def getTranslation(self, mudfile):
        """Gets the translation from MUD to MSPL."""
        return mudtranslator.translate(mudfile if isinstance(mudfile, dict) else json.loads(mudfile))
    
    def getMUDUrlFromDSP(self, dsp_json):
        """Compatibility: redirects to mud_service.get_mud_url_from_dsp()"""
        return self.mud_service.get_mud_url_from_dsp(dsp_json)
    
    def getMUD(self, dsp, device_identifier):
        """Compatibility: redirects to mud_service.get_mud()"""
        return self.mud_service.get_mud(dsp, device_identifier)
    
    def get_threats_from_threatmud_manager(self, device_identifier=None):
        """Compatibility: redirects to threat_service.get_threats()"""
        return self.threat_service.get_threats(device_identifier)
    
    def get_threat_by_id_from_threatmud_manager(self, threat_id):
        """Compatibility: redirects to threat_service.get_threat_by_id()"""
        return self.threat_service.get_threat_by_id(threat_id)
    
    def parseMitigationsTMUD(self, mitigation_actions):
        """Compatibility: redirects to parse_mitigations_tmud()"""
        return parse_mitigations_tmud(mitigation_actions)
    
    def parseMitigationsMUD(self, mitigation_actions):
        """Compatibility: redirects to parse_mitigations_mud()"""
        return parse_mitigations_mud(mitigation_actions)
    
    def getTMUDFile(self, tmudurl):
        """Compatibility: redirects to threat_service.get_tmud_file()"""
        return self.threat_service.get_tmud_file(tmudurl)
    
    def getGendspFromIdsp(self, idsp_id):
        """Compatibility: redirects to device_service.get_gendsp_from_idsp()"""
        return self.device_service.get_gendsp_from_idsp(idsp_id)
    
    def register_dsp(self, device):
        """Compatibility: redirects to device_service.register_dsp()"""
        return self.device_service.register_dsp(device)
    
    def printAllDevices(self):
        """Compatibility: redirects to device_service.get_all_devices_dict()"""
        return self.device_service.get_all_devices_dict()
    
    def start(self):
        """Starts the Kafka consumer (only if Kafka is available)"""
        if not KAFKA_AVAILABLE:
            logging.warning("Kafka is not available. Cannot start Kafka consumer.")
            return
        
        self.configBroker()
        
        if self.consumer is None:
            logging.error("Kafka consumer is not initialized. Cannot start.")
            return
        
        try:
            logging.info("Device and Domain Manager is starting")
            logging.info("Starting broker interface")
            logging.info("Broker topics: " + ','.join(self.topics))
            self.consumer.subscribe(self.topics)
            
            while True:
                # poll messages
                message = self.consumer.poll(1)
                
                if message != None:
                    if message.topic() == self.topicKnownDevice:
                        logging.info("New message received from Network Boostrapping monitor")
                        self.process_message_topic_Bootsrapping_monitor(message.value())
                    
                    elif message.topic() == self.topicThreatRequest:
                        logging.info("New message received from SIEM-SOAR with a Request")
                        self.handleSIEMRequest(message.value())
        
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logging.error(f"Error in Kafka consumer loop: {e}", exc_info=True)
        finally:
            if self.consumer:
                try:
                    logging.info("Leaving group and committing final offsets")
                    self.consumer.close()
                except Exception as e:
                    logging.error(f"Error closing Kafka consumer: {e}", exc_info=True)
            logging.info("Device and Domain manager is closing")
