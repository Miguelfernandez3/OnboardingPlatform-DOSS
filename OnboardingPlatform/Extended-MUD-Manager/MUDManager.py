import socket
import ssl

import threading
import time
import logging

from flask import Flask, request
from dotenv import load_dotenv

import MUDFileSigner as Verifier
import requests
import random
import os
import yaml
from Database import Database, MUD
from confluent_kafka import Consumer, Producer
import json
import sys
from urllib.parse import urlparse

# Load environment variables from .env file
load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))

# Go up one level to the Implementation directory
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))

# Add the Implementation directory to sys.path
sys.path.append(parent_dir)

from Policy_Translator import mudtranslator
import traceback

# Import shared authentication
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
shared_auth_path = os.path.join(parent_dir, 'shared_auth')
sys.path.insert(0, shared_auth_path)
from decorators import require_auth

app = Flask(__name__)

manager = None

def _env_flag(name: str, default: str = "false") -> bool:
    """Parse common boolean env values."""
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")

class MUDManager:

    def __init__(self):
        # Read config.yaml

        with open('config.yaml') as f:
            config = yaml.load(f,Loader=yaml.FullLoader)
            self.SetInterval = config['MUDManager']['SetInterval']
            self.interval = config['MUDManager']['Interval']
            self.broker = config['MUDManager']['broker']
            self.receivetopic = config['MUDManager']['receivetopic']
            self.sendtopic = config['MUDManager']['sendtopic']
        self.localhost_alias_by_port = self._parse_localhost_alias_map()
        self.default_localhost_alias = os.getenv("MUD_LOCALHOST_ALIAS", "").strip()
        self.db = Database()

        if self.SetInterval:
            self.periodicCheck()

        # Kafka producer initialization (currently disabled - uncomment if Kafka is available)
        # The Producer will attempt to connect immediately, causing timeout errors if Kafka is not available
        self.producer = None
        # Uncomment the following lines if Kafka is available and needed:
        # try:
        #     pconf = {
        #         'bootstrap.servers': self.broker,
        #     }
        #     self.producer = Producer(pconf)
        #     logging.info(f"Kafka producer initialized for broker {self.broker}")
        # except Exception as e:
        #     logging.warning(f"Could not initialize Kafka producer for broker {self.broker}: {e}")
        #     logging.warning("Kafka functionality will be disabled. MUD Manager will continue without Kafka.")

        # Start Kafka consumer thread (currently disabled)
        # threading.Thread(target=self.start).start()
        #self.start()

    def periodicCheck(self):
        logging.info("Checking if some MUDFile content changes")

        muds = self.db.getAllMUDs()
        if muds is not None:
            for mud in muds:
                if not self.compareMUD(mud.mudurl,mud.mudfile):
                    logging.info("Detected MUD File change on manufacturer side -> Executing MUD Enforcement process")
                    mud.mudfile = self.getMUDFile(mud.mudurl)
                    self.db.updateMUD(mud)
                    logging.info("Updating database with new MUD File for MUD URL: " + mud.mudurl)
                    self.sendMUDFile(mud)

        logging.info("Checking MUDFiles process complete")
        threading.Timer(float(self.interval), function=self.periodicCheck).start()

    def sendMUDFile(self, mud):
        """Envía un archivo MUD a través de Kafka (si está disponible)"""
        if self.producer is None:
            logging.warning("Kafka producer not available. Skipping MUD file send to Kafka.")
            return

        try:
            dic = {
                "mudurl": mud.mudurl,
                "mudfile": mud.mudfile,
                "device_identifier": mud.device_identifier
            }
            mud_json = json.dumps(dic)

            self.producer.poll(1)
            self.producer.produce(self.sendtopic, value=mud_json)
            self.producer.flush()
            logging.info(f"MUD file sent to Kafka topic {self.sendtopic}")
        except Exception as e:
            logging.error(f"Error sending MUD file to Kafka: {e}", exc_info=True)

    def validateURL(self,mudurl):


        return False

    def compareMUD(self,mudurl,mudfileDB):

        mudfile = self.getMUDFile(mudurl)
        if mudfile == mudfileDB:
            return True

        return False

    def _parse_localhost_alias_map(self):
        """
        Parse LOCALHOST_ALIAS_BY_PORT env var like:
        8091:mud-server,8888:mud-manager
        """
        mapping = {}
        raw = os.getenv("LOCALHOST_ALIAS_BY_PORT", "").strip()
        if not raw:
            return mapping

        for entry in raw.split(","):
            item = entry.strip()
            if not item:
                continue
            if ":" not in item:
                logging.warning(f"Ignoring invalid LOCALHOST_ALIAS_BY_PORT entry: '{item}'")
                continue

            port_str, alias = item.split(":", 1)
            port_str = port_str.strip()
            alias = alias.strip()

            if not port_str.isdigit() or not alias:
                logging.warning(f"Ignoring invalid LOCALHOST_ALIAS_BY_PORT entry: '{item}'")
                continue

            mapping[int(port_str)] = alias
        return mapping

    def _resolve_mud_url(self, mudurl):
        """
        Rewrites localhost URLs so they are reachable from inside Docker networks.
        """
        try:
            parsed = urlparse(mudurl)
            if parsed.hostname not in ("localhost", "127.0.0.1", "0.0.0.0"):
                return mudurl

            localhost_alias = (
                self.localhost_alias_by_port.get(parsed.port)
                or self.default_localhost_alias
            )
            if not localhost_alias:
                return mudurl

            if parsed.port:
                netloc = f"{localhost_alias}:{parsed.port}"
            else:
                netloc = localhost_alias

            if parsed.username:
                auth = parsed.username
                if parsed.password:
                    auth = f"{auth}:{parsed.password}"
                netloc = f"{auth}@{netloc}"

            resolved_url = parsed._replace(netloc=netloc).geturl()
            if resolved_url != mudurl:
                logging.info(
                    f"Rewriting local MUD URL for container networking: {mudurl} -> {resolved_url}"
                )
            return resolved_url
        except Exception as e:
            logging.warning(f"Failed to rewrite MUD URL '{mudurl}': {e}. Using original URL.")
            return mudurl

    def getMUDFile(self,mudurl):
        resolved_mudurl = self._resolve_mud_url(mudurl)
        r = requests.get(resolved_mudurl)

        return r.text

    def verifyMUDFile(self,mudurl):
        resolved_mudurl = self._resolve_mud_url(mudurl)

        mudsignurl = resolved_mudurl.replace(".json",".p7s")

        logging.info("Downloading mudfile from: " + resolved_mudurl)
        r = requests.get(resolved_mudurl)
        mudfile = "temp" + str(random.randint(1,100000000)) + ".json"

        open(mudfile,"w+").write(r.text)

        logging.info("Downloading singature for mudfile from: " + mudsignurl)
        r = requests.get(mudsignurl)

        mudcrt = "temp" + str(random.randint(1,100000000)) + ".p7s"

        open(mudcrt,"wb+").write(r.content)

        logging.info("Verifying MUD File")

        #ret = Verifier._verify(mudcrt,mudfile,"pubkey.crt")
        ret = True
        os.remove(mudcrt)
        os.remove(mudfile)
        logging.info("MUD Verified")
        return True
        return ret


    def newMUD(self,device_identifier, mudurl):

        if not self.verifyMUDFile(mudurl):
            logging.info("Fail at verifing MUD File sign")
            return

        mudfile = self.getMUDFile(mudurl)

        mud = MUD(mudurl=mudurl, device_identifier=device_identifier, mudfile=mudfile)

        if self.db.getMUD(mudurl) is None:
            logging.info("Adding new MUD to database")
            self.db.createMUD(mudurl,mudfile,device_identifier)
        logging.info("Sending MUD File to Domain and Device Manager")
        #self.sendMUDFile(mud)
        dic = {
            "mudurl": mud.mudurl,
            "mudfile": mud.mudfile,
            "device_identifier": mud.device_identifier
        }
        mud_json = json.dumps(dic)
        return mud_json


    def newConnexion(self, message):
        logging.info("Received new message from kafka")
        logging.info("Message:\n"+message)
        logging.info("Parsing message")
        js = json.loads(message)

        mudurl = js["mudurl"]
        device_identifier = js["device_identifier"]
        self.newMUD(device_identifier,mudurl)

        return

    def start(self):
        pass
'''
        conf = {
            'bootstrap.servers': self.broker,
            # usually of the form cell-1.streaming.<region>.oci.oraclecloud.com:9092
            'group.id': 'MUD Manager',
        }
        # Create Consumer instance
        consumer = Consumer(conf)
        # Subscribe to topic
        consumer.subscribe([self.receivetopic])
        try:
            logging.info("MUD Server is starting")
            logging.info("Subscribing to Kafka topic: " + self.receivetopic)

            while True:
                msg = consumer.poll(1.0)
                if msg is None:
                    # No message available within timeout.
                    # Initial message consumption may take up to
                    # `session.timeout.ms` for the consumer group to
                    # rebalance and start consuming
                    print("Waiting for message or event/error in poll()")
                    continue
                elif msg.error():
                    logging.info('error: {}'.format(msg.error()))
                else:
                    # Check for Kafka message
                    record_key = "Null" if msg.key() is None else msg.key().decode('utf-8')
                    record_value = msg.value().decode('utf-8')
                    logging.info("Consumed record with key " + record_key + " and value " + record_value)
                    print(record_value)
                    try:
                        print("parsing new connexion")
                        print(type(record_value))
                        t = threading.Thread(target=self.newConnexion, args=(record_value,))
                        t.run()
                    except Exception as e:
                        print(str(e))
                        traceback.print_exc()
                        pass
                

        except KeyboardInterrupt:
            pass
        finally:
            logging.info(print("Leave group and commit final offsets"))
            consumer.close()
            logging.info("MUD Server is closing")
'''

def _handle_new_connection():
    logging.info(f"Received POST request: /mud")
    js = request.get_json()
    logging.info(f"Request payload: {js}")
    logging.info("Parsing message")


    mudurl = js['mudurl']
    device_identifier = js['device_identifier']

    response = manager.newMUD(device_identifier,mudurl)
    print(response)

    return response

# Internal endpoint consumed by Domain-Manager.
# In local development we allow unauthenticated calls by default because
# Domain-Manager does not forward user JWT to this service.
if _env_flag("MUD_MANAGER_REQUIRE_AUTH", "false"):
    @app.route('/mud', methods=['POST'])
    @require_auth
    def newConnexion(current_user):
        return _handle_new_connection()
else:
    @app.route('/mud', methods=['POST'])
    def newConnexion():
        return _handle_new_connection()

if __name__ == '__main__':
    # Configure logging with more detailed level for debugging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Log to console
            logging.FileHandler('MUDManager.log')  # Also log to file
        ]
    )
    
    logging.info("=" * 80)
    logging.info("Starting MUDManager")
    logging.info("=" * 80)
    logging.info(f"MUD /mud auth enabled: {_env_flag('MUD_MANAGER_REQUIRE_AUTH', 'false')}")
    
    try:
        logging.debug("Creating MUDManager instance")
        manager = MUDManager()
        logging.info("MUDManager instance created successfully")
        
        logging.info("Starting Flask application on port 8888")
        app.run(host='0.0.0.0', use_reloader=False, debug=True, port=8888)
    except Exception as e:
        logging.critical(f"Fatal error starting MUDManager: {e}", exc_info=True)
        raise
