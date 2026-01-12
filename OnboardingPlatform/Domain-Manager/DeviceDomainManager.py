import time

import logging
import yaml
import Database
from confluent_kafka import Consumer, Producer
import json
# Import Flask for API REST server, create app variable and import routes from routes.py file
from flask import Flask, request, jsonify
import requests
import threading
import os
import sys
import ERADriver

current_dir = os.path.dirname(os.path.abspath(__file__))

# Go up one level to the Implementation directory
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))

# Add the Implementation directory to sys.path
sys.path.append(parent_dir)

from Policy_Translator import mudtranslator
from lxml import etree
from datetime import datetime, timezone
app = Flask(__name__)

# Configure CORS
CORS(app)

dadm = None

class DeviceDomainManager:

    def __init__(self):

        # Read config.yaml

        with open('config.yaml') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
            self.broker = config['DeviceDomainManager']['Broker']
            self.FEAM_server = config['DeviceDomainManager']['FEAM_server']
            self.FEAM_sessionId = config['DeviceDomainManager']['FEAM_sessionId']
            self.ThreatMUDManager_url = config['DeviceDomainManager'].get('ThreatMUDManager_url', 'http://localhost:8889')
            self.MUDManager_url = config['DeviceDomainManager'].get('MUDManager_url', 'http://localhost:8888')

            self.topics = []

        self.db = Database.Database()

        self.prepareFEAM()

        pconf = {
            'bootstrap.servers': self.broker,
        }
        #self.producer = Producer(pconf)

        #threading.Thread(target=self.start).start()
        #self.start()

    def prepareFEAM(self):
        url = f"{self.FEAM_server}/init"

        payload = f'{{"sessionId": "{self.FEAM_sessionId}"}}'
        headers = {
            'user-agent': "vscode-restclient",
            'content-type': "application/json"
            }

        logging.info("Initializing FEAM server")
        response = requests.request("POST", url, data=payload, headers=headers)
        if response.status_code == 200:
            logging.info("FEAM server is prepared")
        else:
            logging.error("FEAM server is not prepared")
            logging.error(response.text)
            
        print(response.text)

        logging.info("Stopping Forget Pin Timer")
        url = f"{self.FEAM_server}/stopForgetPinTimer"
        payload = f'{{"sessionId": "{self.FEAM_sessionId}"}}'
        headers = {
            'user-agent': "vscode-restclient",
            'content-type': "application/json"
            }

        response = requests.request("POST", url, data=payload, headers=headers)

        if response.status_code == 200:
            logging.info("FEAM Forget Pin Timer is stopped")
        else:
            logging.error("FEAM Forget Pin Timer is not stopped")
            logging.error(response.text)
        print(response.text)

    def FEAMcheckPIN(self, pin=1234):
        url = f"{self.FEAM_server}/checkPin"

        payload = f"{{\"sessionId\": \"{self.FEAM_sessionId}\",\"pinCode\": \"{pin}\"}}"
        headers = {
            'user-agent': "vscode-restclient",
            'content-type': "application/json"
            }
        response = requests.request("POST", url, data=payload, headers=headers)
        print(response.text)

    def FEAMgetDSPfromID(self, dsp_id):
        self.FEAMcheckPIN()
        url = f"{self.FEAM_server}/callResourceServer"

        payload = f"{{\"sessionId\": \"{self.FEAM_sessionId}\",\"functionId\":\"0bfae6a6-9281-4d38-ad18-b851ef9b86a0\",\"operationId\":\"0bfae6a6-4637-487c-a71a-9cba257304af\",\"extraValues\": [\"{{\\\"id\\\":\\\"{dsp_id}\\\",\\\"version\\\":\\\"1.0.0\\\"}}\"]}}"
        headers = {
            'user-agent': "vscode-restclient",
            'content-type': "application/json"
            }

        response = requests.request("POST", url, data=payload, headers=headers)

        return response.text




    def configBroker(self):
        

        conf = {
            'bootstrap.servers': self.broker,
            'group.id': 'DomainDeviceManager'
        }

        # Create Consumer instance
        self.consumer = Consumer(conf)


    def reconfigureDevice(self, mitigation_data, device):
        
        message = ERADriver.compose_message_change_signature()

        logging.info(f"Sending reconfiguration for device {device.identifier}. Reconfiguration message: {message}")
        ERADriver.send_message(device.ip, message, edk = device.edk)
        

    def getTranslation(self, mudfile):
        return mudtranslator.translate(json.loads(mudfile))

    def getMUDUrlFromDSP(self, dsp_json):
        """
        Extract MUD file URL from DSP JSON by looking for links with rel="MUD file"
        
        Args:
            dsp_json: The DSP JSON object (either string or dict)
        
        Returns:
            str: The href URL of the MUD file, or None if not found
        """
        try:
            # If dsp_json is a string, parse it
            if isinstance(dsp_json, str):
                dsp_data = json.loads(dsp_json)
            else:
                dsp_data = dsp_json
            
            # Navigate to components in the DSP structure
            components = dsp_data.get('dspFile', {}).get('doss-dsp', {}).get('local-definitions', {}).get('components', [])
            
            # Iterate through components to find MUD file links
            for component in components:
                links = component.get('links', [])
                for link in links:
                    # Check if this link is a MUD file
                    if link.get('rel') == 'MUD file':
                        return link.get('href')
            
            # If no MUD file found
            logging.warning("No MUD file link found in DSP")
            return None
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logging.error(f"Error parsing DSP JSON for MUD URL: {e}")
            return None
        
    def getMUD(self, dsp, device_identifier):
        """
        Obtiene el archivo MUD del MUD Manager vía API REST
        
        Args:
            dsp: Digital Service Passport (JSON)
            device_identifier: Identificador del dispositivo
        
        Returns:
            dict: Diccionario con 'mudurl' y 'mudfile', o None si hay error
        """
        logging.debug(f"getMUD called for device_identifier: {device_identifier}")
        try:
            mudurl = self.getMUDUrlFromDSP(dsp)
            if not mudurl:
                logging.error("No MUD URL found in DSP")
                return None
            
            mudurl = mudurl.replace(".json", "")
            logging.debug(f"Extracted MUD URL: {mudurl}")
            
            dic = {
                'mudurl': mudurl,
                'device_identifier': device_identifier
            }

            headers = {
                'Content-Type': 'application/json'
            }
            
            url = f"{self.MUDManager_url}/mud"
            logging.debug(f"Making HTTP POST request to: {url}")
            logging.debug(f"MUDManager_url: {self.MUDManager_url}")
            logging.debug(f"Request payload: {dic}")
            
            response = requests.post(url, json=dic, headers=headers, timeout=10)
            logging.debug(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    js = response.json()
                    logging.debug(f"Response JSON keys: {list(js.keys()) if isinstance(js, dict) else 'N/A'}")
                    
                    mudfile = js.get('mudfile')
                    if not mudfile:
                        logging.error("Response JSON does not contain 'mudfile' key")
                        return None
                    
                    ret = {
                        'mudurl': mudurl,
                        'mudfile': mudfile
                    }
                    
                    logging.info(f"Successfully retrieved MUD file for device {device_identifier}")
                    return ret
                except ValueError as json_err:
                    logging.error(f"JSON decode error: {json_err}, response text: {response.text[:200]}")
                    return None
            else:
                logging.error(f"MUDManager returned status {response.status_code}: {response.text[:200]}")
                return None
                
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Could not connect to MUDManager at {self.MUDManager_url}: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logging.error(f"Timeout connecting to MUDManager at {self.MUDManager_url}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error getting MUD from MUDManager: {e}", exc_info=True)
            return None


    def get_threats_from_threatmud_manager(self, device_identifier=None):
        """
        Obtiene threats del ThreatMUDManager vía API REST
        
        Args:
            device_identifier: Si se proporciona, filtra por device_identifier
        
        Returns:
            list: Lista de threats o lista vacía si hay error
        """
        logging.debug(f"get_threats_from_threatmud_manager called with device_identifier={device_identifier}, type={type(device_identifier)}")
        try:
            # Validar device_identifier
            if device_identifier is None:
                logging.debug("device_identifier is None, getting all threats")
                url = f"{self.ThreatMUDManager_url}/api/threats"
            else:
                # Asegurarse de que device_identifier es string válido
                device_identifier_str = str(device_identifier) if device_identifier else None
                if not device_identifier_str or device_identifier_str == 'None':
                    logging.warning(f"Invalid device_identifier: {device_identifier}, getting all threats instead")
                    url = f"{self.ThreatMUDManager_url}/api/threats"
                else:
                    url = f"{self.ThreatMUDManager_url}/api/threats/device/{device_identifier_str}"
            
            logging.debug(f"Making HTTP GET request to: {url}")
            logging.debug(f"ThreatMUDManager_url: {self.ThreatMUDManager_url}")
            
            response = requests.get(url, timeout=5)
            logging.debug(f"Response status code: {response.status_code}")
            logging.debug(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                logging.debug("Response status is 200, parsing JSON")
                try:
                    data = response.json()
                    logging.debug(f"Parsed JSON data type: {type(data)}, keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                    threats = data.get('threats', [])
                    logging.debug(f"Extracted threats: type={type(threats)}, length={len(threats) if isinstance(threats, list) else 'N/A'}")
                    
                    # Validar que threats es una lista
                    if not isinstance(threats, list):
                        logging.error(f"threats is not a list, it's {type(threats)}: {threats}")
                        return []
                    
                    logging.info(f"Successfully retrieved {len(threats)} threats from ThreatMUDManager")
                    return threats
                except ValueError as json_err:
                    logging.error(f"JSON decode error: {json_err}, response text: {response.text[:200]}")
                    return []
            else:
                logging.warning(f"ThreatMUDManager returned status {response.status_code}: {response.text[:200]}")
                return []
        except requests.exceptions.ConnectionError as e:
            logging.warning(f"Could not connect to ThreatMUDManager at {self.ThreatMUDManager_url}: {e}")
            return []
        except requests.exceptions.Timeout as e:
            logging.warning(f"Timeout connecting to ThreatMUDManager at {self.ThreatMUDManager_url}: {e}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error getting threats from ThreatMUDManager: {e}", exc_info=True)
            return []
    
    def get_threat_by_id_from_threatmud_manager(self, threat_id):
        """
        Obtiene un threat específico por ID del ThreatMUDManager vía API REST
        
        Args:
            threat_id: ID del threat
        
        Returns:
            dict: Datos del threat o None si no se encuentra
        """
        logging.debug(f"get_threat_by_id_from_threatmud_manager called with threat_id={threat_id}, type={type(threat_id)}")
        try:
            # Validar threat_id
            if threat_id is None:
                logging.warning("threat_id is None")
                return None
            
            threat_id_str = str(threat_id)
            url = f"{self.ThreatMUDManager_url}/api/threats/{threat_id_str}"
            
            logging.debug(f"Making HTTP GET request to: {url}")
            response = requests.get(url, timeout=5)
            logging.debug(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                logging.debug("Response status is 200, parsing JSON")
                try:
                    threat_data = response.json()
                    logging.debug(f"Parsed threat data type: {type(threat_data)}, keys: {list(threat_data.keys()) if isinstance(threat_data, dict) else 'N/A'}")
                    logging.info(f"Successfully retrieved threat {threat_id} from ThreatMUDManager")
                    return threat_data
                except ValueError as json_err:
                    logging.error(f"JSON decode error: {json_err}, response text: {response.text[:200]}")
                    return None
            elif response.status_code == 404:
                logging.debug(f"Threat {threat_id} not found (404)")
                return None
            else:
                logging.warning(f"ThreatMUDManager returned status {response.status_code}: {response.text[:200]}")
                return None
        except requests.exceptions.ConnectionError as e:
            logging.warning(f"Could not connect to ThreatMUDManager at {self.ThreatMUDManager_url}: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logging.warning(f"Timeout connecting to ThreatMUDManager at {self.ThreatMUDManager_url}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error getting threat {threat_id} from ThreatMUDManager: {e}", exc_info=True)
            return None

    def parseMitigationsTMUD(self, mitigation_actions):
        
        print("ma0" + mitigation_actions[0])
        print("ma1" + mitigation_actions[1])
        root = etree.XML(mitigation_actions[0].encode("utf-8"))

        # Extract models-affected
        models_affected = root.xpath('//models-affected/text()')

        # Initialize an empty list to store the dictionaries
        config_actions = []

        # Iterate through each configuration-action element
        for action in root.xpath('//configuration-action'):
            action_dict = {}

            # Iterate through each child of the action element
            for child in action:
                if child.tag not in action_dict:
                    action_dict[child.tag] = {}
                for grandchild in child:
                    # Handle multiple elements with the same tag (e.g., software-fix-url)
                    if grandchild.tag in action_dict[child.tag]:
                        if isinstance(action_dict[child.tag][grandchild.tag], list):
                            action_dict[child.tag][grandchild.tag].append(grandchild.text)
                        else:
                            action_dict[child.tag][grandchild.tag] = [action_dict[child.tag][grandchild.tag],
                                                                      grandchild.text]
                    else:
                        action_dict[child.tag][grandchild.tag] = grandchild.text

            # Add the action dictionary to the list
            config_actions.append(action_dict)

        config_conditions = []

        # Iterate through each configuration-condition element
        for condition in root.xpath('//configuration-condition'):
            condition_dict = {}

            # Iterate through each child of the condition element
            for child in condition:
                if child.tag not in condition_dict:
                    condition_dict[child.tag] = {}
                for grandchild in child:
                    if grandchild.tag not in condition_dict[child.tag]:
                        condition_dict[child.tag][grandchild.tag] = {}
                    for greatgrandchild in grandchild:
                        condition_dict[child.tag][grandchild.tag][greatgrandchild.tag] = greatgrandchild.text

            # Add the condition dictionary to the list
            config_conditions.append(condition_dict)

        mitigation_data = {
            "action": config_actions,
            "condition": config_conditions,
            "models": models_affected
        }
        print(mitigation_data)
        return mitigation_data
    def parseMitigationsMUD(self, mitigation_actions):
   
        print(mitigation_actions)
        print(type(mitigation_actions))
        tree = etree.fromstring(mitigation_actions.encode("utf-8"))

        config_actions = []
        for action in tree.findall('.//configuration-action'):
            action_dict = {}

            # Iterate through each child of the action element
            for child in action:
                action_dict[child.tag] = {grandchild.tag: grandchild.text for grandchild in child}

            # Add the action dictionary to the list
            config_actions.append(action_dict)

        print(config_actions)

        return config_actions

    def getTMUDFile(self, tmudurl):
        # Get TMUD File from URL
        try:
            data = {
                'tmudurl': tmudurl
            }
            response = requests.post(self.ThreatMUDManager_url + "tmud", json=data)
            if response.status_code == 200:
                logging.info("TMUD File retrieved successfully")
                return response.text
            else:
                logging.error("Failed to retrieve TMUD file")
                return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Error retrieving TMUD file: {e}")
            return None

    def getDSP(self, DSP_id):
        dspResponse = self.FEAMgetDSPfromID(DSP_id)
        logging.warning(f"New DSP File retrieved from DSPP. Updating entry in database.")
        #print(dspResponse)
        jsonResponse = json.loads(dspResponse.replace('\"', '"'))
        #print(jsonResponse)
        if jsonResponse['status'] == 'ok':
            dspJSON = jsonResponse['responseJson']
            print("DSP JSON: " + dspJSON)
            return dspJSON
        dspJSON = '{"signature":"RYFiVhs5YFNJQ7eR90ki1ryeGWRcI99iD4CSPaUfuPlYXjycjfrpyp/TP0z6Y63ndajAtj6BnuOqzSjHPL4hQvkRaaew/fqI12k3Xl19LK3ZABXmIFjOu7lfi3kHyMIVCgsDCSVJOBmJjDEW/d+Rr9gyoISuCkpPRFiw/6gelIg=","certificate":"MIIBxTCCAS6gAwIBAgIIZ04S/ociQiowDQYJKoZIhvcNAQELBQAwGzEZMBcGA1UEAxMQVGVzdCBDZXJ0aWZpY2F0ZTAeFw0yNTA0MjIxMTM1MDNaFw0yNjA0MjMxMTM1MDNaMBsxGTAXBgNVBAMTEFRlc3QgQ2VydGlmaWNhdGUwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAKuCNWExJ/0JBuguUiGYeanS6ieB4N2NhQDOG+w5tXxamuHSLvfAbjHQTJfaZSOBjdOOQbYYD7CUYcb3iOHEPYBVS7vN+lVfE4bAiNg7e440ms8Fv7xc4yMj3BLKMHrTJV3ohvK/+udww3DR5DLJ6tjdIx3myZqKjmcq8FmLTo8PAgMBAAGjEjAQMA4GA1UdDwEB/wQEAwIFoDANBgkqhkiG9w0BAQsFAAOBgQCGL32J9m28yRFZRG57W1Z3lDGpsOy6fOVCOCjO1EcmZboMyggg9oHEFmLwarMXOe2xVys1kT9oBgmNha96eTrFH1n6PuwN3WF6un/y6xNn+dP2XvkNKLHR7Mi/wVk25mW6UFbq8KtKqZ9yQHLKCu6QrqvzkF5RelVZn3A34GgirA==","dspFile":{"doss-dsp":{"uuid":"477ac7cd-c71e-444a-a124-f80c2f47393b","metadata":{"title":"Attacker genDSP","last-modified":"2025-07-09T16:40:00.000000","version":"1.0.0","dsp-model-version":"1.0.0"},"local-definitions":{"components":[{"uuid":"864b7845-54fd-44b4-8c4f-04a5ce648113","type":"this-system","title":"Attacker","description":"Attacker environment for vulnerability scanning and exploitation","links":[{"href":"attacker_sbom.json","rel":"SBOM file","media-type":"application/vnd.cyclonedx+json"},{"href":"http://localhost:8091/attacker_mud.json","rel":"MUD file","media-type":"application/mud+json"}],"status":{"state":"operational"}}]}}}}'
        print("DSP JSON: " + dspJSON)
        return dspJSON

    def register_dsp(self, device):
        existing_device = self.db.getDevice(device.identifier)
        
        if existing_device is not None:
            logging.info("Device already exists in database.")
            return False
        else:
            logging.warning(f"New device with identifier {device.identifier} joining. Creating entry in database.")
            dsp = self.getDSP(device.dsp_id)
            device.dsp = dsp
            
            ret = self.getMUD(device.dsp, device.identifier)
            if ret is None:
                logging.error(f"Failed to get MUD file for device {device.identifier}. Device registration aborted.")
                return False
            
            device.mudurl = ret['mudurl']
            device.mudfile = ret['mudfile']
            
            self.db.createdevice(device)
            logging.info("Device registered successfully.")
            self.db.printDevice(device)
            return True

    def printAllDevices(self):
        devices = self.db.getAllDevices()
        dvcs = []
        for device in devices:
            dvcs.append(self.db.printDevice(device))
        return dvcs
    
    
    def start(self):
        self.configBroker()

        
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
                        #self.process_message_topic_Bootsrapping_monitor_Threat_MUD(message.value())

        except KeyboardInterrupt:
            pass
        finally:
            logging.info(print("Leave group and commit final offsets"))
            self.consumer.close()
            logging.info("Device and Domain manager is closing")


# ==================== HELPER FUNCTIONS ====================

def device_to_dict(device):
    """Convierte un objeto Device de SQLAlchemy a diccionario según DeviceData interface"""
    # Formatear fechas a ISO 8601 si existen
    # Usar getattr() para compatibilidad con dispositivos antiguos que no tienen estos campos
    created_at = None
    updated_at = None
    created_at_val = getattr(device, 'created_at', None)
    updated_at_val = getattr(device, 'updated_at', None)
    
    if created_at_val:
        created_at = created_at_val.isoformat()
    if updated_at_val:
        updated_at = updated_at_val.isoformat()
    
    return {
        'id': device.identifier or str(device.id),
        'name': getattr(device, 'name', None) or device.model or '',
        'type': getattr(device, 'type', None) or '',
        'manufacturer': getattr(device, 'manufacturer', None) or '',
        'model': device.model or '',
        'status': getattr(device, 'status', None) or 'active',
        'createdAt': created_at,
        'updatedAt': updated_at,
        'ip': device.ip,
        'mac': device.mac,
        'identifier': device.identifier,
        'mudurl': device.mudurl,
        'mudfile': device.mudfile,
        'mitigation_actions': device.mitigation_actions,
        'inventory_id': device.dsp_id,
        'edk': getattr(device, 'edk', None)
    }

def parse_mitigation_xml(mitigation_xml):
    """Parsea XML de mitigación y extrae información estructurada"""
    try:
        if isinstance(mitigation_xml, list):
            mitigation_xml = mitigation_xml[0] if mitigation_xml else ''
        
        if not mitigation_xml:
            return None
            
        root = etree.XML(str(mitigation_xml).encode("utf-8"))
        
        # Extract models-affected
        models_affected = root.xpath('//models-affected/text()')
        
        # Extract configuration-actions
        config_actions = []
        for action in root.xpath('//configuration-action'):
            action_dict = {}
            for child in action:
                if child.tag not in action_dict:
                    action_dict[child.tag] = {}
                for grandchild in child:
                    if grandchild.tag in action_dict[child.tag]:
                        if isinstance(action_dict[child.tag][grandchild.tag], list):
                            action_dict[child.tag][grandchild.tag].append(grandchild.text)
                        else:
                            action_dict[child.tag][grandchild.tag] = [
                                action_dict[child.tag][grandchild.tag],
                                grandchild.text
                            ]
                    else:
                        action_dict[child.tag][grandchild.tag] = grandchild.text
            config_actions.append(action_dict)
        
        # Extract configuration-conditions
        config_conditions = []
        for condition in root.xpath('//configuration-condition'):
            condition_dict = {}
            for child in condition:
                if child.tag not in condition_dict:
                    condition_dict[child.tag] = {}
                for grandchild in child:
                    if grandchild.tag not in condition_dict[child.tag]:
                        condition_dict[child.tag][grandchild.tag] = {}
                    for greatgrandchild in grandchild:
                        condition_dict[child.tag][grandchild.tag][greatgrandchild.tag] = greatgrandchild.text
            config_conditions.append(condition_dict)
        
        return {
            'actions': config_actions,
            'conditions': config_conditions,
            'models_affected': models_affected
        }
    except Exception as e:
        logging.error(f"Error parsing mitigation XML: {e}")
        return None

@app.route('/', methods=['GET'])
def list_endpoints():
    endpoints = [
        {
            'method': 'POST',
            'route': '/register_device',
            'description': 'Route to register device for the software upgrade use case.',
            'parameters': {
                'type': 'JSON',
                'fields': [
                    'mac: string',
                    'firmware_version: string',
                    'name: string',
                    'group_id: string',
                    'device_id: string',
                    'v_cred: JSON'
                ]
            }
        },
        {
            'method': 'POST',
            'route': '/register_software',
            'description': 'Route to register software versions in software upgrade case.',
            'parameters': {
                'type': 'JSON',
                'fields': [
                    'sw_identifier: string',
                    'sw_version: string',
                    'name: string'
                ]
            }
        },
        {
            'method': 'POST',
            'route': '/get_software',
            'description': 'Route to register software versions in software upgrade case.',
            'parameters': {
                'type': 'JSON',
                'fields': [
                    'sw_identifier: string',
                    'v_cred: JSON'
                ]
            }
        },
        {
            'method': 'POST',
            'route': '/update_status',
            'description': 'Update device status after update in the software upgrade use case.',
            'parameters': {
                'type': 'JSON',
                'fields': [
                    'device_id: string',
                    'update_id: string',
                    'status: string'
                ]
            }
        },
        {
            'method': 'POST',
            'route': '/boostrapping',
            'description': 'New device is finished the bootstrapping proccess',
            'parameters': {
                'type': 'JSON',
                'fields': [
                    'uuid: string',
                    'device: string',
                    'ip_address: string',
                    "mud-url: string"
                ]
            }
        }
    ]
    return endpoints

@app.route('/dsp', methods=['GET', 'POST'])
def post_DSP():
    if request.method == 'POST':
        data = request.get_json()
        
        logging.info(f"Received DSP ID: {data.get('DSP_id')} for Device ID: {data.get('device_id')}")
        device = dadm.db.parseDeviceJson(data)
        if dadm.register_dsp(device):
            return jsonify({'status': 'success', 'message': 'Data received and processed'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Device already exists'}), 400
    elif request.method == 'GET':
        return jsonify({'status': 'success', 'message': 'GET request received'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid request method'}), 405
    

@app.route('/devices', methods=['GET'])
def printDevices():
    devices = dadm.printAllDevices()

    return jsonify({'status': 'success', 'message': 'Devices printed to console', 'data': devices}), 200

@app.route('/newthreat', methods=['POST'])
def newThreat():
    data = request.get_json()
    logging.info(f"Received new threat: {data}")
    return jsonify({'status': 'success', 'message': 'New threat received'}), 200

# ==================== API ENDPOINTS (Frontend) ====================

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Obtiene la lista de todos los dispositivos"""
    try:
        devices = dadm.db.getAllDevices()
        if devices is None:
            devices = []
        
        devices_list = []
        for device in devices:
            device_dict = device_to_dict(device)
            devices_list.append(device_dict)
        
        return jsonify({
            'devices': devices_list
        }), 200
    except DatabaseError as e:
        logging.error(f"Database error getting devices: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error getting devices: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>', methods=['GET'])
def get_device(device_id):
    """Obtiene un dispositivo específico por ID"""
    try:
        device = dadm.db.getDevice(device_id)
        if device is None:
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404
        
        device_dict = device_to_dict(device)
        return jsonify({
            'device': device_dict
        }), 200
    except DatabaseError as e:
        logging.error(f"Database error getting device {device_id}: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error getting device {device_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>', methods=['PUT'])
def update_device(device_id):
    """Actualiza información de un dispositivo"""
    try:
        device = dadm.db.getDevice(device_id)
        if device is None:
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404
        
        data = request.get_json()
        
        # Actualizar campos permitidos
        if 'name' in data:
            device.name = data['name']
        if 'ip' in data:
            device.ip = data['ip']
        if 'mac' in data:
            device.mac = data['mac']
        if 'model' in data:
            device.model = data['model']
        if 'type' in data:
            device.type = data['type']
        if 'manufacturer' in data:
            device.manufacturer = data['manufacturer']
        if 'status' in data:
            device.status = data['status']
        if 'edk' in data:
            device.edk = data['edk']
        
        success = dadm.db.updateDevice(device)
        if success:
            updated_device = dadm.db.getDevice(device_id)
            return jsonify({
                'device': device_to_dict(updated_device)
            }), 200
        else:
            return jsonify({
                'error': 'Failed to update device',
                'code': 'UPDATE_FAILED',
                'details': {}
            }), 500
    except DatabaseError as e:
        logging.error(f"Database error updating device {device_id}: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error updating device {device_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>', methods=['DELETE'])
def delete_device(device_id):
    """Elimina un dispositivo"""
    try:
        device = dadm.db.getDevice(device_id)
        if device is None:
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404
        
        success = dadm.db.deleteDevice(device)
        if success:
            return jsonify({}), 200
        else:
            return jsonify({
                'error': 'Failed to delete device',
                'code': 'DELETE_FAILED',
                'details': {}
            }), 500
    except DatabaseError as e:
        logging.error(f"Database error deleting device {device_id}: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error deleting device {device_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>/passport', methods=['GET'])
def get_device_passport(device_id):
    """Obtiene el pasaporte digital (DSP) de un dispositivo"""
    try:
        device = dadm.db.getDevice(device_id)
        if device is None:
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404
        
        # El DSP está almacenado en device.dsp como JSON string
        dsp_data = {}
        if device.dsp:
            try:
                dsp_data = json.loads(device.dsp)
            except json.JSONDecodeError:
                dsp_data = {'raw': device.dsp}
        
        return jsonify({
            'deviceId': device_id,
            'data': dsp_data
        }), 200
    except DatabaseError as e:
        logging.error(f"Database error getting passport for device {device_id}: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error getting passport for device {device_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>/mud', methods=['GET'])
def get_device_mud(device_id):
    """Obtiene el archivo MUD de un dispositivo"""
    try:
        device = dadm.db.getDevice(device_id)
        if device is None:
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404
        
        mud_data = {}
        if device.mudfile:
            try:
                mud_json = json.loads(device.mudfile)
                mud_data = mud_json
            except json.JSONDecodeError:
                mud_data = {'raw': device.mudfile}
        
        # Extraer información del MUD según especificación
        mud_info = {
            'id': device.mudurl or f'mud-{device_id}',
            'deviceId': device_id,
            'mudVersion': None,
            'mudUrl': device.mudurl,
            'lastUpdate': None,
            'cacheValidity': None,
            'isSupported': True,
            'systeminfo': None,
            'mfgName': None,
            'documentation': None,
            'modelName': None,
            'mudData': mud_data
        }
        
        # Intentar extraer metadata del MUD
        if isinstance(mud_data, dict):
            mud_section = mud_data.get('ietf-mud:mud', {})
            mud_info['mudVersion'] = mud_section.get('mud-version')
            mud_info['mfgName'] = mud_section.get('mfg-name', '')
            mud_info['modelName'] = mud_section.get('model-name', '')
            mud_info['documentation'] = mud_section.get('documentation', '')
            mud_info['systeminfo'] = mud_section.get('systeminfo', '')
            mud_info['lastUpdate'] = mud_section.get('last-update', '')
            mud_info['cacheValidity'] = mud_section.get('cache-validity')
            mud_info['isSupported'] = mud_section.get('is-supported', True)
        
        return jsonify(mud_info), 200
    except DatabaseError as e:
        logging.error(f"Database error getting MUD for device {device_id}: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error getting MUD for device {device_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>/policies', methods=['GET'])
def get_device_policies(device_id):
    """Obtiene las políticas MSPL aplicadas a un dispositivo"""
    try:
        device = dadm.db.getDevice(device_id)
        if device is None:
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404
        
        policies = []
        
        # 1. Políticas MUD: Se derivan dinámicamente del mudfile (no se persisten)
        if device.mudfile:
            try:
                mud_json = json.loads(device.mudfile)
                mspl_list = mudtranslator.translate(mud_json)
                
                for idx, mspl_xml in enumerate(mspl_list):
                    policies.append({
                        'id': f'mud-policy-{idx}',
                        'deviceId': device_id,
                        'name': f'MUD Policy {idx + 1}',
                        'msplXml': mspl_xml,
                        'status': 'active',
                        'appliedAt': None,
                        'enforcementStatus': 'completed'
                    })
            except Exception as e:
                logging.error(f"Error translating MUD to MSPL: {e}")
        
        # 2. Políticas persistentes: Leer de tabla Policy
        try:
            persisted_policies = dadm.db.getPoliciesByDevice(device_id)
            for policy in persisted_policies:
                policies.append({
                    'id': str(policy.id),
                    'deviceId': device_id,
                    'name': policy.name,
                    'msplXml': policy.mspl_xml,
                    'status': policy.status,
                    'appliedAt': policy.applied_at.isoformat() if policy.applied_at else None,
                    'enforcementStatus': policy.enforcement_status
                })
        except Exception as e:
            logging.error(f"Error retrieving persisted policies for device {device_id}: {e}", exc_info=True)
        
        # 3. NO incluir mitigation_actions como política
        # mitigation_actions es solo para mitigaciones temporales de threats
        
        return jsonify({
            'policies': policies
        }), 200
    except DatabaseError as e:
        logging.error(f"Database error getting policies for device {device_id}: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error getting policies for device {device_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>/apply-idsp2', methods=['POST'])
def apply_idsp2(device_id):
    """Aplica un IDSP2 ID a un dispositivo"""
    try:
        data = request.get_json()
        idsp2_id = data.get('idsp2Id') if data else None
        
        if not idsp2_id:
            return jsonify({
                'error': 'idsp2Id is required',
                'code': 'INVALID_REQUEST',
                'details': {}
            }), 400
        
        device = dadm.db.getDevice(device_id)
        if device is None:
            # Si el dispositivo no existe, crear uno nuevo
            device = dadm.db.parseDeviceJson({
                'device_id': device_id,
                'DSP_id': idsp2_id
            })
        
        # Registrar el DSP usando el método existente
        device.dsp_id = idsp2_id
        result = dadm.register_dsp(device)
        
        if result:
            return jsonify({
                'status': 'pending',
                'message': 'IDSP2 application initiated'
            }), 200
        else:
            return jsonify({
                'error': 'Failed to apply IDSP2',
                'code': 'APPLICATION_FAILED',
                'details': {}
            }), 500
    except DatabaseError as e:
        logging.error(f"Database error applying IDSP2 to device {device_id}: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error applying IDSP2 to device {device_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>/apply-policy', methods=['POST'])
def apply_policy(device_id):
    """Aplica una política MSPL directamente a un dispositivo"""
    try:
        device = dadm.db.getDevice(device_id)
        if device is None:
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404
        
        # Obtener XML del body (puede venir como XML o JSON con campo msplXml)
        content_type = request.headers.get('Content-Type', '')
        mspl_xml = None
        policy_name = None
        
        if 'application/xml' in content_type:
            mspl_xml = request.data.decode('utf-8')
        elif 'application/json' in content_type:
            data = request.get_json()
            mspl_xml = data.get('msplXml') or data.get('mspl')
            policy_name = data.get('name')
            
            if not mspl_xml:
                return jsonify({
                    'error': 'msplXml is required',
                    'code': 'INVALID_REQUEST',
                    'details': {}
                }), 400
        else:
            return jsonify({
                'error': 'Content-Type must be application/xml or application/json',
                'code': 'INVALID_CONTENT_TYPE',
                'details': {}
            }), 400
        
        # Crear política en tabla Policy (separada de mitigaciones)
        try:
            policy_name_final = policy_name or f'Policy {datetime.now().isoformat()}'
            policy = dadm.db.createPolicy(
                device_id=device_id,
                name=policy_name_final,
                mspl_xml=mspl_xml,
                policy_type='manual',
                source='user',
                status='pending',
                enforcement_status='pending'
            )
            
            if policy:
                # Llamar a reconfigureDevice para aplicar la política
                dadm.reconfigureDevice(mspl_xml, device)
                
                return jsonify({
                    'status': 'pending',
                    'message': 'Policy application initiated'
                }), 200
            else:
                return jsonify({
                    'error': 'Failed to create policy',
                    'code': 'POLICY_CREATION_FAILED',
                    'details': {}
                }), 500
        except DatabaseError as e:
            logging.error(f"Database error creating policy for device {device_id}: {e.message}", exc_info=True)
            return jsonify({
                'error': e.message,
                'code': 'DATABASE_ERROR',
                'details': {
                    'original_error': str(e.original_error) if e.original_error else None
                }
            }), 500
    except DatabaseError as e:
        logging.error(f"Database error applying policy to device {device_id}: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error applying policy to device {device_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>/policies/<policy_id>/enforcement-status', methods=['POST'])
def update_policy_enforcement_status(device_id, policy_id):
    """
    Callback endpoint para recibir actualizaciones de enforcement status
    desde el DSP Enforcer/ERA después de aplicar una política
    
    Request Body:
    {
        "status": "completed" | "failed",
        "message": "Enforcement completed successfully",
        "timestamp": "2024-01-20T14:30:00Z" (opcional)
    }
    """
    try:
        logging.info(f"Received enforcement status update request for policy {policy_id} on device {device_id}")
        
        # 1. Validar request body
        data = request.get_json()
        if not data:
            logging.warning(f"Empty request body for enforcement status update")
            return jsonify({
                'error': 'Request body is required',
                'code': 'INVALID_REQUEST',
                'details': {}
            }), 400
        
        new_status = data.get('status')
        message = data.get('message', '')
        timestamp_str = data.get('timestamp')
        
        logging.debug(f"Enforcement status update data: status={new_status}, message={message}, timestamp={timestamp_str}")
        
        # 2. Validar status
        if new_status not in ['completed', 'failed']:
            logging.warning(f"Invalid status received: {new_status}")
            return jsonify({
                'error': 'Invalid status. Must be "completed" or "failed"',
                'code': 'INVALID_STATUS',
                'details': {
                    'received_status': new_status,
                    'valid_statuses': ['completed', 'failed']
                }
            }), 400
        
        # 3. Obtener política
        policy = dadm.db.getPolicy(policy_id)
        if policy is None:
            logging.warning(f"Policy {policy_id} not found")
            return jsonify({
                'error': f'Policy with id {policy_id} not found',
                'code': 'POLICY_NOT_FOUND',
                'details': {}
            }), 404
        
        # 4. Verificar que la política pertenece al dispositivo
        if policy.device_id != device_id:
            logging.warning(f"Policy {policy_id} does not belong to device {device_id}. Policy belongs to {policy.device_id}")
            return jsonify({
                'error': 'Policy does not belong to this device',
                'code': 'POLICY_DEVICE_MISMATCH',
                'details': {
                    'policy_device_id': policy.device_id,
                    'requested_device_id': device_id
                }
            }), 400
        
        # 5. Actualizar estado
        old_enforcement_status = policy.enforcement_status
        old_status = policy.status
        
        policy.enforcement_status = new_status
        policy.status = 'active' if new_status == 'completed' else 'failed'
        
        # 6. Actualizar applied_at si se proporciona timestamp
        if timestamp_str:
            try:
                # Parsear timestamp (soporta ISO 8601 con y sin Z)
                if timestamp_str.endswith('Z'):
                    timestamp_str = timestamp_str.replace('Z', '+00:00')
                policy.applied_at = datetime.fromisoformat(timestamp_str)
                logging.debug(f"Applied timestamp from request: {policy.applied_at}")
            except ValueError as e:
                logging.warning(f"Invalid timestamp format '{timestamp_str}': {e}. Using current time.")
                policy.applied_at = datetime.now(timezone.utc)
        else:
            # Si no se proporciona timestamp y aún no tiene applied_at, usar ahora
            if policy.applied_at is None:
                policy.applied_at = datetime.now(timezone.utc)
                logging.debug(f"Set applied_at to current time: {policy.applied_at}")
        
        # 7. Guardar cambios usando updatePolicy
        policy.updated_at = datetime.now(timezone.utc)
        success = dadm.db.updatePolicy(policy)
        
        if not success:
            logging.error(f"Failed to update policy {policy_id} in database")
            return jsonify({
                'error': 'Failed to update policy',
                'code': 'UPDATE_FAILED',
                'details': {}
            }), 500
        
        logging.info(f"Policy {policy_id} enforcement status updated: {old_enforcement_status} -> {new_status}, status: {old_status} -> {policy.status}")
        
        # 8. Retornar respuesta
        return jsonify({
            'status': 'success',
            'message': 'Enforcement status updated',
            'policy': {
                'id': str(policy.id),
                'deviceId': policy.device_id,
                'name': policy.name,
                'status': policy.status,
                'enforcementStatus': policy.enforcement_status,
                'appliedAt': policy.applied_at.isoformat() if policy.applied_at else None
            }
        }), 200
        
    except DatabaseError as e:
        logging.error(f"Database error updating enforcement status: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error updating enforcement status: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>/enforcement-status', methods=['GET'])
def get_enforcement_status(device_id):
    """Obtiene el estado de enforcement de un dispositivo basado en políticas reales"""
    try:
        logging.debug(f"Getting enforcement status for device {device_id}")
        
        device = dadm.db.getDevice(device_id)
        if device is None:
            logging.warning(f"Device {device_id} not found")
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404
        
        # Obtener todas las políticas persistentes del dispositivo
        try:
            persisted_policies = dadm.db.getPoliciesByDevice(device_id)
            logging.debug(f"Found {len(persisted_policies)} persisted policies for device {device_id}")
        except Exception as e:
            logging.error(f"Error retrieving persisted policies for enforcement status: {e}", exc_info=True)
            persisted_policies = []
        
        # Analizar estados de enforcement
        total_policies = len(persisted_policies)
        completed = 0
        pending = 0
        failed = 0
        unknown = 0
        
        policy_details = []
        
        for policy in persisted_policies:
            enforcement_status = policy.enforcement_status or 'unknown'
            
            if enforcement_status == 'completed':
                completed += 1
            elif enforcement_status == 'failed':
                failed += 1
            elif enforcement_status == 'pending':
                pending += 1
            else:
                unknown += 1
            
            policy_details.append({
                'id': str(policy.id),
                'name': policy.name,
                'enforcementStatus': enforcement_status,
                'status': policy.status
            })
        
        logging.debug(f"Enforcement status breakdown: completed={completed}, pending={pending}, failed={failed}, unknown={unknown}")
        
        # Determinar estado general
        if total_policies == 0:
            # No hay políticas persistentes, verificar si tiene MUD
            has_mud = bool(device.mudfile)
            overall_status = 'pending'
            message = 'No policies applied' if not has_mud else 'Only MUD policies (status unknown)'
        elif failed > 0:
            overall_status = 'failed'
            message = f'{failed} policy(ies) failed enforcement'
        elif pending > 0 or unknown > 0:
            overall_status = 'pending'
            message = f'{pending + unknown} policy(ies) pending enforcement'
        else:
            overall_status = 'completed'
            message = 'All policies are enforced'
        
        logging.info(f"Enforcement status for device {device_id}: {overall_status} - {message}")
        
        return jsonify({
            'status': overall_status,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': {
                'totalPolicies': total_policies,
                'completed': completed,
                'pending': pending,
                'failed': failed,
                'unknown': unknown,
                'policies': policy_details
            }
        }), 200
    except DatabaseError as e:
        logging.error(f"Database error getting enforcement status for device {device_id}: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error getting enforcement status for device {device_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>/threats', methods=['GET'])
def get_device_threats(device_id):
    """Obtiene las threats asociadas a un dispositivo"""
    logging.info(f"get_device_threats called for device_id: {device_id}")
    try:
        logging.debug(f"Getting device from database: {device_id}")
        device = dadm.db.getDevice(device_id)
        if device is None:
            logging.warning(f"Device {device_id} not found in database")
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404
        
        logging.debug(f"Device found: identifier={device.identifier}, type={type(device.identifier)}")
        
        # Validar que device.identifier existe
        if not device.identifier:
            logging.warning(f"Device {device_id} has no identifier, returning empty threats list")
            return jsonify({
                'threats': []
            }), 200
        
        # Obtener threats del ThreatMUDManager vía API REST
        logging.debug(f"Calling get_threats_from_threatmud_manager with identifier: {device.identifier}")
        threats_data = dadm.get_threats_from_threatmud_manager(device.identifier)
        logging.debug(f"Received threats_data: type={type(threats_data)}, length={len(threats_data) if isinstance(threats_data, list) else 'N/A'}")
        
        # Validar que threats_data es una lista
        if not isinstance(threats_data, list):
            logging.error(f"threats_data is not a list: {type(threats_data)} = {threats_data}")
            threats_data = []
        
        threats = []
        logging.debug(f"Processing {len(threats_data)} threats")
        for idx, threat_data in enumerate(threats_data):
            try:
                logging.debug(f"Processing threat {idx}: type={type(threat_data)}, keys={list(threat_data.keys()) if isinstance(threat_data, dict) else 'N/A'}")
                if not isinstance(threat_data, dict):
                    logging.warning(f"threat_data[{idx}] is not a dict: {type(threat_data)}")
                    continue
                
                threats.append({
                    'id': threat_data.get('id'),
                    'identifier': threat_data.get('identifier'),
                    'threat_mud_url': threat_data.get('threat_mud_url'),
                    'threat_mud_file': threat_data.get('threat_mud_file'),
                    'mitigation_actions': threat_data.get('mitigation_actions'),
                    'deviceId': device_id
                })
            except Exception as e:
                logging.error(f"Error processing threat_data[{idx}]: {e}", exc_info=True)
                continue
        
        logging.info(f"Returning {len(threats)} threats for device {device_id}")
        return jsonify({
            'threats': threats
        }), 200
    except DatabaseError as e:
        logging.error(f"Database error getting threats for device {device_id}: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error getting threats for device {device_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>/mitigations', methods=['GET'])
def get_device_mitigations(device_id):
    """Obtiene las mitigaciones asociadas a un dispositivo"""
    try:
        device = dadm.db.getDevice(device_id)
        if device is None:
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404
        
        mitigations = []
        
        # Si el dispositivo tiene mitigation_actions, crear una mitigación
        if device.mitigation_actions:
            mitigation_data = parse_mitigation_xml(device.mitigation_actions)
            if mitigation_data:
                mitigations.append({
                    'id': f'mitigation-{device_id}',
                    'deviceId': device_id,
                    'name': 'Device Mitigation',
                    'description': 'Mitigation applied to device',
                    'mitigation_actions': device.mitigation_actions,
                    'is_enforced': True,
                    'last_enforced': datetime.now().isoformat(),
                    'enforcement_timestamp': datetime.now().isoformat()
                })
        
        # También buscar mitigaciones relacionadas con threats del dispositivo
        logging.debug(f"Getting threats for mitigations, device identifier: {device.identifier}")
        if device.identifier:
            threats_data = dadm.get_threats_from_threatmud_manager(device.identifier)
            logging.debug(f"Received threats_data for mitigations: type={type(threats_data)}, length={len(threats_data) if isinstance(threats_data, list) else 'N/A'}")
            
            # Validar que threats_data es una lista
            if not isinstance(threats_data, list):
                logging.error(f"threats_data is not a list in mitigations: {type(threats_data)}")
                threats_data = []
            
            for idx, threat_data in enumerate(threats_data):
                try:
                    logging.debug(f"Processing threat {idx} for mitigation: type={type(threat_data)}")
                    if not isinstance(threat_data, dict):
                        logging.warning(f"threat_data[{idx}] is not a dict: {type(threat_data)}")
                        continue
                    
                    mitigation_actions = threat_data.get('mitigation_actions')
                    if mitigation_actions:
                        logging.debug(f"Adding mitigation for threat {threat_data.get('id')}")
                        mitigations.append({
                            'id': f'threat-mitigation-{threat_data.get("id")}',
                            'deviceId': device_id,
                            'threatId': threat_data.get('id'),
                            'name': f'Threat Mitigation {threat_data.get("id")}',
                            'description': f'Mitigation for threat {threat_data.get("threat_mud_url")}',
                            'mitigation_actions': mitigation_actions,
                            'is_enforced': False,
                            'last_enforced': None,
                            'enforcement_timestamp': None
                        })
                except Exception as e:
                    logging.error(f"Error processing threat_data[{idx}] for mitigation: {e}", exc_info=True)
                    continue
        else:
            logging.warning(f"Device {device_id} has no identifier, skipping threat mitigations")
        
        return jsonify({
            'mitigations': mitigations
        }), 200
    except DatabaseError as e:
        logging.error(f"Database error getting mitigations for device {device_id}: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error getting mitigations for device {device_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>/mitigations/<mitigation_id>/enforce', methods=['POST'])
def enforce_mitigation(device_id, mitigation_id):
    """Aplica (enforce) una mitigación en un dispositivo"""
    try:
        device = dadm.db.getDevice(device_id)
        if device is None:
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404
        
        # Buscar la mitigación
        # Si es una mitigación de threat, obtenerla del ThreatMUDManager vía API REST
        logging.debug(f"Enforcing mitigation {mitigation_id} for device {device_id}")
        if mitigation_id.startswith('threat-mitigation-'):
            threat_id_str = mitigation_id.replace('threat-mitigation-', '')
            logging.debug(f"Extracted threat_id: {threat_id_str}")
            
            threat_data = dadm.get_threat_by_id_from_threatmud_manager(threat_id_str)
            logging.debug(f"Received threat_data: type={type(threat_data)}, is None: {threat_data is None}")
            
            if threat_data:
                if not isinstance(threat_data, dict):
                    logging.error(f"threat_data is not a dict: {type(threat_data)}")
                else:
                    logging.debug(f"threat_data keys: {list(threat_data.keys())}")
                    mitigation_actions = threat_data.get('mitigation_actions')
                    logging.debug(f"mitigation_actions: type={type(mitigation_actions)}, is None: {mitigation_actions is None}")
                    
                    if mitigation_actions:
                        logging.info(f"Applying mitigation actions to device {device_id}")
                        # Aplicar la mitigación al dispositivo
                        success = dadm.db.updateDeviceMitigationActions(device_id, mitigation_actions)
                        logging.debug(f"Device update success: {success}")
                        
                        if success:
                            # Llamar a reconfigureDevice para aplicar la mitigación
                            # Necesitamos obtener el device actualizado para reconfigureDevice
                            logging.debug(f"Calling reconfigureDevice for device {device_id}")
                            try:
                                # Obtener device actualizado para reconfigureDevice
                                updated_device = dadm.db.getDevice(device_id)
                                if updated_device:
                                    dadm.reconfigureDevice(mitigation_actions, updated_device)
                                    logging.info(f"Successfully enforced mitigation {mitigation_id}")
                            except Exception as e:
                                logging.error(f"Error in reconfigureDevice: {e}", exc_info=True)
                            
                            return jsonify({
                                'mitigation': {
                                    'id': mitigation_id,
                                    'deviceId': device_id,
                                    'threatId': threat_id_str,
                                    'name': f'Threat Mitigation {threat_id_str}',
                                    'mitigation_actions': mitigation_actions,
                                    'is_enforced': True,
                                    'last_enforced': datetime.now().isoformat(),
                                    'enforcement_timestamp': datetime.now().isoformat()
                                }
                            }), 200
                    else:
                        logging.warning(f"threat_data has no mitigation_actions")
            else:
                logging.warning(f"threat_data is None for threat_id {threat_id_str}")
        
        return jsonify({
            'error': f'Mitigation with id {mitigation_id} not found',
            'code': 'MITIGATION_NOT_FOUND',
            'details': {}
        }), 404
    except DatabaseError as e:
        logging.error(f"Database error enforcing mitigation {mitigation_id} for device {device_id}: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error enforcing mitigation {mitigation_id} for device {device_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

@app.route('/api/devices/<device_id>/mitigations/<mitigation_id>/revoke', methods=['POST'])
def revoke_mitigation(device_id, mitigation_id):
    """Revoca (revoke) una mitigación en un dispositivo"""
    try:
        device = dadm.db.getDevice(device_id)
        if device is None:
            return jsonify({
                'error': f'Device with id {device_id} not found',
                'code': 'DEVICE_NOT_FOUND',
                'details': {}
            }), 404
        
        # Revocar la mitigación eliminando mitigation_actions
        success = dadm.db.updateDeviceMitigationActions(device_id, None)
        

        if success:
            # Llamar a reconfigureDevice para revocar la mitigación
            dadm.reconfigureDevice(None, device)
            logging.info(f"Successfully revoked mitigation {mitigation_id}")
            return jsonify({
                'mitigation': {
                    'id': mitigation_id,
                    'deviceId': device_id,
                    'mitigation_actions': None,
                    'is_enforced': False,
                    'last_enforced': None,
                    'enforcement_timestamp': None
                }
            }), 200
        else:
            return jsonify({
                'error': 'Failed to revoke mitigation',
                'code': 'REVOKE_FAILED',
                'details': {}
            }), 500
    except DatabaseError as e:
        logging.error(f"Database error revoking mitigation {mitigation_id} for device {device_id}: {e.message}", exc_info=True)
        return jsonify({
            'error': e.message,
            'code': 'DATABASE_ERROR',
            'details': {
                'original_error': str(e.original_error) if e.original_error else None
            }
        }), 500
    except Exception as e:
        logging.error(f"Unexpected error revoking mitigation {mitigation_id} for device {device_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'code': 'INTERNAL_ERROR',
            'details': {}
        }), 500

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
        
        logging.info("Starting Flask application on port 4321")
        app.run(host='0.0.0.0', use_reloader=False, debug=True, port=4321)
    except Exception as e:
        logging.critical(f"Fatal error starting DeviceDomainManager: {e}", exc_info=True)
        raise

