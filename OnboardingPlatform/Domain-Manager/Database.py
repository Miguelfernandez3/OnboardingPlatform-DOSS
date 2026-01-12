from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
import json

# Create a base class for our classes definitions
Base = declarative_base()


# Excepción personalizada para errores de base de datos
class DatabaseError(Exception):
    """Excepción personalizada para errores de base de datos"""
    def __init__(self, message, original_error=None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)
    
    def __str__(self):
        if self.original_error:
            return f"{self.message}: {self.original_error}"
        return self.message


# Define the Device model
class Device(Base):
    __tablename__ = 'device'

    id = Column(Integer, primary_key=True)
    ip = Column(String)
    mac = Column(String)
    model = Column(String)
    identifier = Column(String)
    mudurl = Column(String)
    mudfile = Column(String)
    mitigation_actions = Column(String)
    dsp_id = Column(String)
    dsp = Column(String)

class Threat(Base):
    __tablename__ = 'threat'
    id = Column(Integer, primary_key=True)
    identifier = Column(String)
    threat_mud_url = Column(String)
    threat_mud_file = Column(String)
    mitigation_actions = Column(String)

class Database():
    def __init__(self):

        # Create an engine that stores data in the local directory's DeviceDomainManager.db file.
        self.engine = create_engine('sqlite:///DeviceDomainManager.db')

        # Create all tables in the engine
        Base.metadata.create_all(self.engine)

        # Create a Session class which will be used to create a session
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def createDevice(self, ip, mac, model, identifier, mudurl, mudfile, mitigation_actions, dsp_id, dsp):
        # Create and add new entry
        new_device = Device(ip=ip, mac=mac, model=model, identifier=identifier, mudurl=mudurl,
                            mudfile=mudfile, mitigation_actions=mitigation_actions, dsp_id=dsp_id, dsp=dsp)
        try:
            if self.session.query(Device).filter_by(identifier=identifier).first() is None:
                self.session.add(new_device)
                self.session.commit()
                return True
            return False
        except:
            return False

    def createThreat(self, identifier, threat_mud_url, threat_mud_file, mitigation_actions):

        new_threat = Threat(identifier=identifier, threat_mud_url=threat_mud_url,
                            threat_mud_file=threat_mud_file, mitigation_actions=mitigation_actions)
        try:
            if self.session.query(Threat).filter_by(threat_mud_url=threat_mud_url).first() is None:
                self.session.add(new_threat)
                self.session.commit()
                return True
            return False
        except:
            return False


    def createdevice(self, device):
        return self.createDevice(device.ip, device.mac, device.model, device.identifier, device.mudurl, device.mudfile,
                                 device.mitigation_actions, device.dsp_id, device.dsp)

    def createThreat(self, threat):
        return self.createThreat(threat.identifier, threat.threat_mud_url, threat.threat_mud_file,
                                 threat.mitigation_actions)

    def getDevice(self, identifier):
        try:
            device = self.session.query(Device).filter_by(identifier=identifier).first()
            return device
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving device with identifier {identifier}", e)
        except Exception as e:
            raise DatabaseError(f"Unexpected error retrieving device with identifier {identifier}", e)

    def getDevicesByModel(self, model):
        try:
            devices = self.session.query(Device).filter_by(model=model).all()
            return devices
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving devices with model {model}", e)
        except Exception as e:
            raise DatabaseError(f"Unexpected error retrieving devices with model {model}", e)

    def getThreat(self, threat_mud_url):
        try:
            threat = self.session.query(Device).filter_by(threat_mud_url=threat_mud_url).first()
            return threat
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving threat with URL {threat_mud_url}", e)
        except Exception as e:
            raise DatabaseError(f"Unexpected error retrieving threat with URL {threat_mud_url}", e)

    def getAllDevices(self):
        try:
            devices = self.session.query(Device).all()
            return devices if devices else []
        except SQLAlchemyError as e:
            raise DatabaseError("Error retrieving all devices", e)
        except Exception as e:
            raise DatabaseError("Unexpected error retrieving all devices", e)

    def getAllThreats(self):
        try:
            threats = self.session.query(Threat).all()
            return threats
        except SQLAlchemyError as e:
            raise DatabaseError("Error retrieving all threats", e)
        except Exception as e:
            raise DatabaseError("Unexpected error retrieving all threats", e)


    def updateDevice(self, device):

        try:
            device_to_update = self.session.query(Device).filter_by(id=device.id).first()
            if device_to_update:
                device_to_update.ip = device.ip
                device_to_update.mac = device.mac
                device_to_update.model = device.model
                device_to_update.identifier = device.identifier
                device_to_update.mudurl = device.mudurl
                device_to_update.mudfile = device.mudfile
                device_to_update.mitigation_actions = device.mitigation_actions
                device_to_update.dsp_id = device.dsp_id
                device_to_update.dsp = device.dsp
                self.session.commit()
                return True
            return False
        except:
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error updating mitigation actions for device {device_identifier}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error updating mitigation actions for device {device_identifier}", e)

    def updateThreat(self, threat):

        try:
            threat_to_update = self.session.query(Threat).filter_by(id=threat.id).first()
            if threat_to_update:
                threat_to_update.identifier = threat.identifier
                threat_to_update.threat_mud_url = threat.threat_mud_url
                threat_to_update.threat_mud_file = threat.threat_mud_file
                threat_to_update.mitigation_actions = threat.mitigation_actions
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error updating threat with id {threat.id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error updating threat with id {threat.id}", e)

    def deleteDevice(self, device):
        try:
            device_to_delete = self.session.query(Device).filter_by(id=device.id).first()
            if device_to_delete:
                self.session.delete(device_to_delete)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error deleting device with id {device.id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error deleting device with id {device.id}", e)

    def deleteThreat(self, threat):
        try:
            threat_to_delete = self.session.query(Threat).filter_by(id=threat.id).first()
            if threat_to_delete:
                self.session.delete(threat_to_delete)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error deleting threat with id {threat.id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error deleting threat with id {threat.id}", e)

    def parseDeviceJson(self, devicejson):
        device_data = devicejson
        return Device(ip=None, mac=None, model=None,
                      identifier=device_data['device_id'], mudurl=None,
                      mudfile=None, mitigation_actions=None, dsp_id=device_data.get('DSP_id'), dsp=None)

    def printDevice(self, device):
        print(
            "IP: " + str(device.ip) + ", MAC: " + str(device.mac) + ", model: " + str(device.model) + ", identifier: " + str(device.identifier) + ", mudurl: " + str(device.mudurl) + ", mudfile: " + str(device.mudfile) + ", mitigation_actions: " + str(device.mitigation_actions) + ", dsp_id: " + str(device.dsp_id) + ", dsp: " + str(device.dsp))
        
        return "IP: " + str(device.ip) + ", MAC: " + str(device.mac) + ", model: " + str(device.model) + ", identifier: " + str(device.identifier) + ", mudurl: " + str(device.mudurl) + ", mudfile: " + str(device.mudfile) + ", mitigation_actions: " + str(device.mitigation_actions) + ", dsp_id: " + str(device.dsp_id) + ", dsp: " + str(device.dsp)
