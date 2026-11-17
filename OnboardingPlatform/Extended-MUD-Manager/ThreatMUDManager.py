import os
import threading
import logging
import traceback
import json
import random

import requests
import yaml
from confluent_kafka import Consumer, Producer
from Database import TMUD, Database
import sys
from urllib.parse import urlparse
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))

# Go up one level to the Implementation directory
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))

# Add the Implementation directory to sys.path
sys.path.append(parent_dir)

# Import shared authentication
shared_auth_path = os.path.join(parent_dir, 'shared_auth')
sys.path.insert(0, shared_auth_path)
from decorators import require_auth

app = Flask(__name__)

manager = None

from Policy_Translator import mudtranslator


def _decode_mitigation_actions(raw_value):
    return Database.deserialize_mspl(raw_value)


def _env_flag(name: str, default: str = "false") -> bool:
    """Parse common boolean env values."""
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def _optional_auth(decorator, enabled: bool):
    """Apply auth decorator only when enabled."""
    if enabled:
        return decorator
    return lambda f: f


AUTH_ENABLED = _env_flag("THREAT_MUD_MANAGER_REQUIRE_AUTH", "false")
auth_guard = _optional_auth(require_auth, AUTH_ENABLED)


class ThreatMUDManager:

    def __init__(self):
        # Read config.yaml

        with open('config.yaml') as f:
            config = yaml.load(f,Loader=yaml.FullLoader)
            self.SetInterval = config['TMUDManager']['SetInterval']
            self.interval = config['TMUDManager']['Interval']
            self.broker = config['TMUDManager']['broker']
            self.receivetopic = config['TMUDManager']['receivetopic']
            self.sendtopic = config['TMUDManager']['sendtopic']
        self.localhost_alias_by_port = self._parse_localhost_alias_map()
        self.default_localhost_alias = os.getenv("THREAT_MUD_LOCALHOST_ALIAS", "").strip()

        self.db = Database()

        if self.SetInterval:
            self.periodicCheck()

        pconf = {
            'bootstrap.servers': self.broker,
        }
        #self.producer = Producer(pconf)
        #self.start()

    def periodicCheck(self):
        logging.info("Checking if some MUDFile content changes")

        tmuds = self.db.getAllTMUDs()
        if tmuds is not None:
            for tmud in tmuds:
                if not self.compareTMUD(tmud.tmudurl, tmud.tmudfile):
                    logging.info("Detected TMUD File change on manufacturer side -> Executing TMUD Enforcement process")
                    tmud.tmudfile = self.getTMUDFile(tmud.tmudurl)
                    self.db.updateTMUD(tmud)
                    logging.info("Updating database with new TMUD File for TMUD URL: " + tmud.tmudurl)
                    self.sendTMUDFile(tmud)

        logging.info("Checking TMUDFiles process complete")
        threading.Timer(float(self.interval), function=self.periodicCheck).start()

    def sendTMUDFile(self, tmud):
        
        out = {
                "tmudmspl": tmud.mspl
        }

        tmud_json = json.dumps(out)

        self.producer.poll(1)
        self.producer.produce(self.sendtopic, value=tmud_json)
        self.producer.flush()
        pass

    def validateURL(self, tmudurl):

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

    def _resolve_tmud_url(self, tmudurl):
        """
        Rewrites localhost URLs so they are reachable from inside Docker networks.
        """
        try:
            parsed = urlparse(tmudurl)
            if parsed.hostname not in ("localhost", "127.0.0.1", "0.0.0.0"):
                return tmudurl

            localhost_alias = (
                self.localhost_alias_by_port.get(parsed.port)
                or self.default_localhost_alias
            )
            if not localhost_alias:
                return tmudurl

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
            if resolved_url != tmudurl:
                logging.info(
                    f"Rewriting local TMUD URL for container networking: {tmudurl} -> {resolved_url}"
                )
            return resolved_url
        except Exception as e:
            logging.warning(f"Failed to rewrite TMUD URL '{tmudurl}': {e}. Using original URL.")
            return tmudurl

    def compareTMUD(self, tmudurl, tmudfileDB):

        tmudfile = self.getTMUDFile(tmudurl)
        if tmudfile == tmudfileDB:
            return True

        return False

    def getTMUDFile(self, tmudurl):
        resolved_tmudurl = self._resolve_tmud_url(tmudurl)
        r = requests.get(resolved_tmudurl)

        return r.text

    def verifyTMUDFile(self, tmudurl):
        resolved_tmudurl = self._resolve_tmud_url(tmudurl)

        tmudsignurl = resolved_tmudurl.replace(".json", ".p7s")

        logging.info("Downloading tmudfile from: " + resolved_tmudurl)
        r = requests.get(resolved_tmudurl)
        tmudfile = "temp" + str(random.randint(1, 100000000)) + ".json"

        open(tmudfile, "w+").write(r.text)

        logging.info("Downloading singature for tmudfile from: " + tmudsignurl)
        r = requests.get(tmudsignurl)

        tmudcrt = "temp" + str(random.randint(1, 100000000)) + ".p7s"

        open(tmudcrt, "wb+").write(r.content)

        logging.info("Verifying TMUD File")

        # ret = Verifier._verify(tmudcrt,tmudfile,"pubkey.crt")
        ret = True
        os.remove(tmudcrt)
        os.remove(tmudfile)
        logging.info("TMUD Verified")
        return True
        return ret

    def getTranslation(self, tmudfile):

        return mudtranslator.translate(json.loads(tmudfile))

    def newTMUD(self, tmudurl):

        tmudfile = self.getTMUDFile(tmudurl)

        js = json.loads(tmudfile)
        print(tmudfile)
        device_identifier = js["ietf-threatmud:mud"]["models-affected"]

        logging.info(f"Translating tmudfile: {tmudurl}")
        mspl = self.getTranslation(tmudfile)
        print(mspl)
        logging.info(f"Transaltion from {tmudurl} -> {mspl}")
        tmud = TMUD(tmudurl=tmudurl, device_identifier=device_identifier, tmudfile=tmudfile, mspl=mspl)

        if self.db.getTMUD(tmudurl) is None:
            logging.info("Adding new TMUD to database")

            self.db.createTMUD(tmudurl, tmudfile, device_identifier, mspl)



        logging.info("Sending TMUD File in MSPL ")
        #self.sendTMUDFile(tmud)
        dic = {
            "tmudurl": tmudurl,
            "tmudfile": tmudfile,
            "mspl": mspl
        }
        mud_json = json.dumps(dic)
        return mud_json

    def newConnexion(self, message):
        logging.info("Received new message from kafka")
        logging.info("Message:\n" + message)
        logging.info("Parsing message")
        js = json.loads(message)

        tmudurl = js["threatuuid"]

        


        self.newTMUD(tmudurl)

        return

    def start(self):

        conf = {
            'bootstrap.servers': self.broker,
            # usually of the form cell-1.streaming.<region>.oci.oraclecloud.com:9092
            'group.id': 'TMUD Manager',
        }
        # Create Consumer instance
        consumer = Consumer(conf)
        # Subscribe to topic
        consumer.subscribe([self.receivetopic])
        try:
            logging.info("TMUD Server is starting")
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
                    try:
                        print("parsing new connexion")
                        print(record_value)
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
            logging.info("TMUD Server is closing")

@app.route('/tmud', methods=['POST'])
@auth_guard
def newtmud(current_user=None):
    logging.info(f"Received POST request: /tmud")
    js = request.get_json()
    logging.info(f"Request payload: {js}")
    logging.info("Parsing message")


    tmudurl = js['tmudurl']
    

    response = manager.newTMUD(tmudurl)
    print(response)

    return response

@app.route('/api/threats', methods=['GET'])
@auth_guard
def get_all_threats(current_user=None):
    """Obtiene todos los threats (TMUDs)"""
    logging.info(f"Received GET request: /api/threats")
    try:
        all_tmuds = manager.db.getAllTMUDs()
        if all_tmuds is None:
            return jsonify({'threats': []}), 200
        
        threats = []
        for tmud in all_tmuds:
            threats.append({
                'id': str(tmud.id),
                'identifier': tmud.device_identifier,
                'threat_mud_url': tmud.tmudurl,
                'threat_mud_file': tmud.tmudfile,
                'mitigation_actions': _decode_mitigation_actions(tmud.mspl)
            })
        
        return jsonify({'threats': threats}), 200
    except Exception as e:
        logging.error(f"Error getting all threats: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/threats/device/<device_identifier>', methods=['GET'])
@auth_guard
def get_threats_by_device(device_identifier, current_user=None):
    """Obtiene todos los threats asociados a un dispositivo"""
    logging.info(f"Received GET request: /api/threats/device/{device_identifier}")
    try:
        all_tmuds = manager.db.getAllTMUDs()
        if all_tmuds is None:
            return jsonify({'threats': []}), 200
        
        threats = []
        for tmud in all_tmuds:
            if tmud.device_identifier == device_identifier:
                threats.append({
                    'id': str(tmud.id),
                    'identifier': tmud.device_identifier,
                    'threat_mud_url': tmud.tmudurl,
                    'threat_mud_file': tmud.tmudfile,
                    'mitigation_actions': _decode_mitigation_actions(tmud.mspl)
                })
        
        return jsonify({'threats': threats}), 200
    except Exception as e:
        logging.error(f"Error getting threats for device {device_identifier}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/threats/<threat_id>', methods=['GET'])
@auth_guard
def get_threat_by_id(threat_id, current_user=None):
    """Obtiene un threat específico por ID"""
    logging.info(f"Received GET request: /api/threats/{threat_id}")
    try:
        threat_id_int = int(threat_id)
        all_tmuds = manager.db.getAllTMUDs()
        if all_tmuds is None:
            return jsonify({
                'error': f'Threat with id {threat_id} not found',
                'code': 'THREAT_NOT_FOUND',
                'details': {}
            }), 404
        
        for tmud in all_tmuds:
            if tmud.id == threat_id_int:
                return jsonify({
                    'id': str(tmud.id),
                    'identifier': tmud.device_identifier,
                    'threat_mud_url': tmud.tmudurl,
                    'threat_mud_file': tmud.tmudfile,
                    'mitigation_actions': _decode_mitigation_actions(tmud.mspl)
                }), 200
        
        return jsonify({
            'error': f'Threat with id {threat_id} not found',
            'code': 'THREAT_NOT_FOUND',
            'details': {}
        }), 404
    except ValueError:
        return jsonify({
            'error': f'Invalid threat id: {threat_id}',
            'code': 'INVALID_THREAT_ID',
            'details': {}
        }), 400
    except Exception as e:
        logging.error(f"Error getting threat {threat_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

if __name__ == '__main__':
    # Configure logging with more detailed level for debugging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Log to console
            logging.FileHandler('ThreatMUDManager.log')  # Also log to file
        ]
    )
    
    logging.info("=" * 80)
    logging.info("Starting ThreatMUDManager")
    logging.info("=" * 80)
    logging.info(f"Threat MUD Manager auth enabled: {AUTH_ENABLED}")
    
    try:
        logging.debug("Creating ThreatMUDManager instance")
        manager = ThreatMUDManager()
        logging.info("ThreatMUDManager instance created successfully")
        
        logging.info("Starting Flask application on port 8889")
        app.run(host='0.0.0.0', use_reloader=False, debug=True, port=8889)
    except Exception as e:
        logging.critical(f"Fatal error starting ThreatMUDManager: {e}", exc_info=True)
        raise
