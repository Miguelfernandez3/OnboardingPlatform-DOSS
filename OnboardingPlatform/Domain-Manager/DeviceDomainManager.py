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
            self.bootstrapping = config['DeviceDomainManager']['EnrolmentIP']

            self.topicKnownDevice = config['DeviceDomainManager']['topicKnownDevice']
            self.topicThreatMUD = config['DeviceDomainManager']['topicTMUDFile']

            self.topicSendMudFile = config['DeviceDomainManager']['topicsendMUDFile']
            self.topicsiemACK = config['DeviceDomainManager']['topicSIEMACK']

            self.topicDADM_Notification = config['DeviceDomainManager']['topicDADMNotification']
            self.topicThreatRequest = config['DeviceDomainManager']['topicThreatRequest']

            self.topics = [self.topicKnownDevice, self.topicThreatRequest]

        self.db = Database.Database()

        pconf = {
            'bootstrap.servers': self.broker,
        }
        self.producer = Producer(pconf)

        threading.Thread(target=self.start).start()
        #self.start()

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


    def sendMUDURL(self, mudurl, device_identifier):

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
        self.process_message_topic_MUDFile(js)

        pass


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


    def printAllDevices(self):
        devices = self.db.getAllDevices()
        for device in devices:
            self.db.printDevice(device)
    
    
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
        print(data)
        
        return jsonify({'status': 'success', 'message': 'Data received and processed'}), 200
    elif request.method == 'GET':
        return jsonify({'status': 'success', 'message': 'GET request received'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid request method'}), 405
    
    
if __name__ == '__main__':
    
    dadm = DeviceDomainManager()


    app.run(host='0.0.0.0', use_reloader=False, debug=True, port=4321)
