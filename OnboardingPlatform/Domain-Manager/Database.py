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
    # Nuevos campos según especificación
    name = Column(String)
    type = Column(String)
    manufacturer = Column(String)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    edk = Column(String)  # Encryption Decryption Key

class Threat(Base):
    __tablename__ = 'threat'
    id = Column(Integer, primary_key=True)
    identifier = Column(String)
    threat_mud_url = Column(String)
    threat_mud_file = Column(String)
    mitigation_actions = Column(String)

class Policy(Base):
    __tablename__ = 'policy'
    
    id = Column(Integer, primary_key=True)
    device_id = Column(String, ForeignKey('device.identifier'))
    name = Column(String)  # Nombre descriptivo de la política
    mspl_xml = Column(String)  # XML MSPL completo
    policy_type = Column(String)  # 'manual' (aplicada manualmente) o 'mud' (si queremos persistir MUD)
    source = Column(String)  # 'user', 'idsp2', 'mud_file'
    status = Column(String, default='pending')  # 'pending', 'active', 'completed', 'failed'
    applied_at = Column(DateTime)
    enforcement_status = Column(String)  # 'pending', 'completed', 'failed', 'unknown'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Database():
    def __init__(self):

        # Create an engine that stores data in the local directory's DeviceDomainManager.db file.
        self.engine = create_engine('sqlite:///DeviceDomainManager.db')

        # Create all tables in the engine
        Base.metadata.create_all(self.engine)

        # Create a Session class which will be used to create a session
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def createDevice(self, ip, mac, model, identifier, mudurl, mudfile, mitigation_actions, dsp_id, dsp, 
                     name=None, type=None, manufacturer=None, status='active', edk=None):
        try:
            # Create and add new entry
            new_device = Device(ip=ip, mac=mac, model=model, identifier=identifier, mudurl=mudurl,
                                mudfile=mudfile, mitigation_actions=mitigation_actions, dsp_id=dsp_id, dsp=dsp,
                                name=name, type=type, manufacturer=manufacturer, status=status, edk=edk)
            if self.session.query(Device).filter_by(identifier=identifier).first() is None:
                self.session.add(new_device)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error creating device with identifier {identifier}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error creating device with identifier {identifier}", e)

    def createThreat(self, identifier, threat_mud_url, threat_mud_file, mitigation_actions):

        new_threat = Threat(identifier=identifier, threat_mud_url=threat_mud_url,
                            threat_mud_file=threat_mud_file, mitigation_actions=mitigation_actions)
        try:
            new_threat = Threat(identifier=identifier, threat_mud_url=threat_mud_url,
                                threat_mud_file=threat_mud_file, mitigation_actions=mitigation_actions)
            if self.session.query(Threat).filter_by(threat_mud_url=threat_mud_url).first() is None:
                self.session.add(new_threat)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error creating threat with URL {threat_mud_url}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error creating threat with URL {threat_mud_url}", e)


    def createdevice(self, device):
        return self.createDevice(device.ip, device.mac, device.model, device.identifier, device.mudurl, device.mudfile,
                                 device.mitigation_actions, device.dsp_id, device.dsp,
                                 getattr(device, 'name', None), getattr(device, 'type', None), 
                                 getattr(device, 'manufacturer', None), getattr(device, 'status', 'active'),
                                 getattr(device, 'edk', None))

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
                device_to_update.name = device.name
                device_to_update.type = device.type
                device_to_update.manufacturer = device.manufacturer
                device_to_update.status = device.status
                device_to_update.edk = device.edk
                device_to_update.updated_at = datetime.now(timezone.utc)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error updating device with id {device.id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error updating device with id {device.id}", e)

    def updateDeviceMitigationActions(self, device_identifier, mitigation_actions):
        """
        Actualiza solo el campo mitigation_actions de un dispositivo usando su identifier.
        Evita conflictos de sesión al hacer la query directamente en lugar de usar un objeto Device.
        
        Args:
            device_identifier: El identifier del dispositivo (string)
            mitigation_actions: El valor a asignar a mitigation_actions (string o None)
        
        Returns:
            bool: True si se actualizó correctamente, False si el dispositivo no existe
        """
        try:
            device_to_update = self.session.query(Device).filter_by(identifier=device_identifier).first()
            if device_to_update:
                device_to_update.mitigation_actions = mitigation_actions
                device_to_update.updated_at = datetime.now(timezone.utc)
                self.session.commit()
                return True
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
        return Device(ip=None, mac=None, model=device_data.get('name') or device_data.get('model'),
                      identifier=device_data['device_id'], mudurl=None,
                      mudfile=None, mitigation_actions=None, dsp_id=device_data.get('DSP_id'), dsp=None,
                      name=device_data.get('name'), type=device_data.get('type'),
                      manufacturer=device_data.get('manufacturer'), status=device_data.get('status', 'active'),
                      edk=device_data.get('edk'))

    def createPolicy(self, device_id, name, mspl_xml, policy_type='manual', source='user', status='pending', enforcement_status='pending'):
        """
        Crea una nueva política MSPL
        
        Args:
            device_id: El identifier del dispositivo
            name: Nombre descriptivo de la política
            mspl_xml: XML MSPL completo
            policy_type: Tipo de política ('manual', 'mud', etc.)
            source: Origen de la política ('user', 'idsp2', 'mud_file')
            status: Estado de la política ('pending', 'active', 'completed', 'failed')
            enforcement_status: Estado de enforcement ('pending', 'completed', 'failed', 'unknown')
        
        Returns:
            Policy: El objeto Policy creado o None si hay error
        """
        try:
            new_policy = Policy(
                device_id=device_id,
                name=name,
                mspl_xml=mspl_xml,
                policy_type=policy_type,
                source=source,
                status=status,
                enforcement_status=enforcement_status,
                applied_at=datetime.now(timezone.utc)
            )
            self.session.add(new_policy)
            self.session.commit()
            return new_policy
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error creating policy for device {device_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error creating policy for device {device_id}", e)

    def getPoliciesByDevice(self, device_id):
        """
        Obtiene todas las políticas de un dispositivo
        
        Args:
            device_id: El identifier del dispositivo
        
        Returns:
            list: Lista de políticas o lista vacía si no hay
        """
        try:
            policies = self.session.query(Policy).filter_by(device_id=device_id).all()
            return policies if policies else []
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving policies for device {device_id}", e)
        except Exception as e:
            raise DatabaseError(f"Unexpected error retrieving policies for device {device_id}", e)

    def getPolicy(self, policy_id):
        """
        Obtiene una política por ID
        
        Args:
            policy_id: El ID de la política
        
        Returns:
            Policy: El objeto Policy o None si no existe
        """
        try:
            policy = self.session.query(Policy).filter_by(id=policy_id).first()
            return policy
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving policy with id {policy_id}", e)
        except Exception as e:
            raise DatabaseError(f"Unexpected error retrieving policy with id {policy_id}", e)

    def updatePolicy(self, policy):
        """
        Actualiza una política existente
        
        Args:
            policy: Objeto Policy con los cambios
        
        Returns:
            bool: True si se actualizó correctamente, False si no existe
        """
        try:
            policy_to_update = self.session.query(Policy).filter_by(id=policy.id).first()
            if policy_to_update:
                policy_to_update.device_id = policy.device_id
                policy_to_update.name = policy.name
                policy_to_update.mspl_xml = policy.mspl_xml
                policy_to_update.policy_type = policy.policy_type
                policy_to_update.source = policy.source
                policy_to_update.status = policy.status
                policy_to_update.applied_at = policy.applied_at
                policy_to_update.enforcement_status = policy.enforcement_status
                policy_to_update.updated_at = datetime.now(timezone.utc)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error updating policy with id {policy.id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error updating policy with id {policy.id}", e)

    def deletePolicy(self, policy_id):
        """
        Elimina una política
        
        Args:
            policy_id: El ID de la política a eliminar
        
        Returns:
            bool: True si se eliminó correctamente, False si no existe
        """
        try:
            policy_to_delete = self.session.query(Policy).filter_by(id=policy_id).first()
            if policy_to_delete:
                self.session.delete(policy_to_delete)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error deleting policy with id {policy_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error deleting policy with id {policy_id}", e)

    def printDevice(self, device):
        print(
            "IP: " + str(device.ip) + ", MAC: " + str(device.mac) + ", model: " + str(device.model) + ", identifier: " + str(device.identifier) + ", mudurl: " + str(device.mudurl) + ", mudfile: " + str(device.mudfile) + ", mitigation_actions: " + str(device.mitigation_actions) + ", dsp_id: " + str(device.dsp_id) + ", dsp: " + str(device.dsp))
        
        return "IP: " + str(device.ip) + ", MAC: " + str(device.mac) + ", model: " + str(device.model) + ", identifier: " + str(device.identifier) + ", mudurl: " + str(device.mudurl) + ", mudfile: " + str(device.mudfile) + ", mitigation_actions: " + str(device.mitigation_actions) + ", dsp_id: " + str(device.dsp_id) + ", dsp: " + str(device.dsp)
