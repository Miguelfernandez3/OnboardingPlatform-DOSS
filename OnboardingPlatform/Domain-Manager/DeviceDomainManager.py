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
from datetime import datetime
app = Flask(__name__)
dadm = None

class DeviceDomainManager:

    def __init__(self):

        # Read config.yaml

        with open('config.yaml') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
            self.broker = config['DeviceDomainManager']['Broker']
            self.FEAM_server = config['DeviceDomainManager']['FEAM_server']
            self.FEAM_sessionId = config['DeviceDomainManager']['FEAM_sessionId']

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

        mudurl = self.getMUDUrlFromDSP(dsp).replace(".json","")
        print("MUD URL: " + mudurl)
        dic = {
            'mudurl': mudurl,
            'device_identifier': device_identifier
        }

        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.post("http://localhost:8888/mud", json=dic, headers=headers)

        js = response.json()
        print(js)

        mudfile = js['mudfile']

        ret = {
            'mudurl': mudurl,
            'mudfile': mudfile
        }

        return ret


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
            response = requests.post("http://localhost:8889/tmud", json=data)
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

if __name__ == '__main__':
    logging.info("Starting Device and Domain manager")
    dadm = DeviceDomainManager()


    app.run(host='0.0.0.0', use_reloader=False, debug=True, port=4321)
