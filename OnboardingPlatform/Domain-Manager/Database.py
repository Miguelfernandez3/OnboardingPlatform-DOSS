import logging
import os
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, inspect, text, Float, Text, UniqueConstraint, and_, or_
from sqlalchemy.engine import make_url
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import datetime, timezone, timedelta
import json

# Create a base class for our classes definitions
Base = declarative_base()

DEFAULT_DATABASE_FILENAME = 'DeviceDomainManager.db'

SQLITE_COLUMN_MIGRATIONS = {
    'device': {
        'name': 'VARCHAR',
        'type': 'VARCHAR',
        'manufacturer': 'VARCHAR',
        'status': "VARCHAR DEFAULT 'active'",
        'created_at': 'DATETIME',
        'updated_at': 'DATETIME',
        'edk': 'VARCHAR',
        'discovered_threat_mud_urls': 'TEXT',
        'pilot_id': 'VARCHAR',
        'enforcement_context': 'TEXT',
    },
    'policy': {
        'device_id': 'VARCHAR',
        'name': 'VARCHAR',
        'mspl_xml': 'VARCHAR',
        'policy_type': 'VARCHAR',
        'source': 'VARCHAR',
        'status': "VARCHAR DEFAULT 'pending'",
        'applied_at': 'DATETIME',
        'enforcement_status': 'VARCHAR',
        'created_at': 'DATETIME',
        'updated_at': 'DATETIME',
        'enforcement_blockers': 'TEXT',
    },
    'user': {
        'email': 'VARCHAR',
        'password_hash': 'VARCHAR',
        'role': "VARCHAR NOT NULL DEFAULT 'user'",
        'is_active': 'BOOLEAN NOT NULL DEFAULT 1',
        'last_login': 'DATETIME',
        'created_at': 'DATETIME',
        'updated_at': 'DATETIME',
        'language': "VARCHAR NOT NULL DEFAULT 'es'",
        'telegram_chat_id': 'VARCHAR',
        'telegram_enabled': 'BOOLEAN NOT NULL DEFAULT 0',
        'in_app_notifications_enabled': 'BOOLEAN NOT NULL DEFAULT 1',
    },
    'enforcement_profile': {
        'auth_type': "VARCHAR DEFAULT 'none'",
        'auth_secret_id': 'INTEGER',
        'allow_mspl_token': 'BOOLEAN NOT NULL DEFAULT 0',
        'created_at': 'DATETIME',
        'updated_at': 'DATETIME',
        'context_spec': 'TEXT',
    },
    'enforcement_mapping': {
        'priority': "INTEGER NOT NULL DEFAULT 100",
        'is_active': 'BOOLEAN NOT NULL DEFAULT 1',
        'created_at': 'DATETIME',
        'updated_at': 'DATETIME',
    },
    'enforcement_secret': {
        'created_at': 'DATETIME',
        'updated_at': 'DATETIME',
    },
    'policy_execution_log': {
        'created_at': 'DATETIME',
        'event_type': "VARCHAR DEFAULT 'policy_execution'",
        'correlation_id': 'VARCHAR',
        'step_name': 'VARCHAR',
        'elapsed_ms': 'FLOAT',
    },
}


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
    name = Column(String)
    type = Column(String)
    manufacturer = Column(String)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    edk = Column(String)  # Encryption Decryption Key
    discovered_threat_mud_urls = Column(Text)
    pilot_id = Column(String)
    # JSON object: operator-supplied {{placeholder}} values for REST enforcement; keys normalized like placeholders
    enforcement_context = Column(Text, nullable=True)

class FeamCatalogSnapshot(Base):
    __tablename__ = 'feam_catalog_snapshot'

    id = Column(Integer, primary_key=True)
    snapshot_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class FeamPilotSyncState(Base):
    __tablename__ = 'feam_pilot_sync_state'

    id = Column(Integer, primary_key=True)
    pilot_id = Column(String, nullable=False, unique=True, index=True)
    last_sync_status = Column(String, nullable=False, default='unknown')
    last_error = Column(Text, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

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
    # pending, completed, failed, unknown, deferred (awaiting operator device/enrichment context)
    enforcement_status = Column(String)
    enforcement_blockers = Column(Text, nullable=True)  # JSON: last known missing [] for UI / ops
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class User(Base):
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default='user', nullable=False)  # 'user' o 'admin'
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    language = Column(String, default='es', nullable=False)
    telegram_chat_id = Column(String, nullable=True)
    telegram_enabled = Column(Boolean, default=False, nullable=False)
    in_app_notifications_enabled = Column(Boolean, default=True, nullable=False)


class DeviceAccessRule(Base):
    """
    Per-user device access grant. A non-admin user sees/manages a device only if
    at least one of their rules matches it. No rules => sees nothing (deny by default).
    Rules are evaluated at query time, so a newly-registered device that matches an
    existing manufacturer/idsp rule appears automatically — nothing to reapply.
    """
    __tablename__ = 'device_access_rule'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    match_kind = Column(String, nullable=False, index=True)   # 'device' | 'manufacturer' | 'idsp'
    match_value = Column(String, nullable=False)              # identifier | manufacturer | dsp_id
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Notification(Base):
    __tablename__ = 'notification'
    __table_args__ = (UniqueConstraint('deduplication_key', name='uq_notification_dedup_key'),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    device_id = Column(String, nullable=True, index=True)
    policy_id = Column(String, nullable=True)
    threat_id = Column(String, nullable=True)
    mitigation_id = Column(String, nullable=True)
    threat_mud_url = Column(Text, nullable=True)
    notification_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default='pending', index=True)
    language = Column(String, nullable=False, default='es')
    message = Column(Text, nullable=False)
    deduplication_key = Column(String, nullable=False)
    error = Column(Text, nullable=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    sent_at = Column(DateTime, nullable=True)


class TelegramLinkToken(Base):
    __tablename__ = 'telegram_link_token'

    id = Column(Integer, primary_key=True)
    token = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EnforcementSecret(Base):
    __tablename__ = 'enforcement_secret'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    ciphertext = Column(Text, nullable=False)
    nonce = Column(String, nullable=False)
    key_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class EnforcementProfile(Base):
    __tablename__ = 'enforcement_profile'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    mode = Column(String, nullable=False, default='rest')
    method = Column(String, nullable=False, default='POST')
    endpoint_template = Column(Text, nullable=True)
    headers_template = Column(Text, nullable=True)
    payload_template = Column(Text, nullable=True)
    timeout_seconds = Column(Float, nullable=False, default=10.0)
    dry_run = Column(Boolean, nullable=False, default=False)
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    auto_enforce_on_registration = Column(Boolean, nullable=False, default=False)
    auth_type = Column(String, nullable=False, default='none')
    auth_secret_id = Column(Integer, ForeignKey('enforcement_secret.id'), nullable=True)
    allow_mspl_token = Column(Boolean, nullable=False, default=False)
    # JSON: { "requirements": [ { "key", "source", "optional", "sensitive", "label" } ] } per enforcement context spec
    context_spec = Column(Text, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    auth_secret = relationship("EnforcementSecret", lazy='joined')


class EnforcementMapping(Base):
    __tablename__ = 'enforcement_mapping'

    id = Column(Integer, primary_key=True)
    match_kind = Column(String, nullable=False, index=True)
    match_value = Column(String, nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey('enforcement_profile.id'), nullable=False, index=True)
    priority = Column(Integer, nullable=False, default=100)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    profile = relationship("EnforcementProfile", lazy='joined')


class DeviceEnforcementSecret(Base):
    """
    Encrypted per-device values for REST enforcement (e.g. Bearer) — same crypto as enforcement_secret.
    device_identifier is device.identifier (UUID string).
    """
    __tablename__ = 'device_enforcement_secret'

    __table_args__ = (UniqueConstraint('device_identifier', 'purpose', name='uq_device_enforcement_purpose'),)

    id = Column(Integer, primary_key=True)
    device_identifier = Column(String, ForeignKey('device.identifier', ondelete='CASCADE'), nullable=False, index=True)
    purpose = Column(String, nullable=False, default='bearer_token')
    ciphertext = Column(Text, nullable=False)
    nonce = Column(String, nullable=False)
    key_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class PolicyExecutionLog(Base):
    __tablename__ = 'policy_execution_log'

    id = Column(Integer, primary_key=True)
    device_id = Column(String, nullable=True, index=True)
    policy_id = Column(String, nullable=True)
    policy_name = Column(String, nullable=True)
    profile_id = Column(Integer, ForeignKey('enforcement_profile.id'), nullable=True, index=True)
    run_mode = Column(String, nullable=False, default='execute')
    # event_type:
    # - policy_execution: enforcement of a policy (REST/ERA/SDN simulated)
    # - onboarding_step: one step of device onboarding timeline
    event_type = Column(String, nullable=False, default='policy_execution', index=True)
    # correlation_id groups all rows (onboarding_step + policy_execution) that belong to one onboarding request.
    correlation_id = Column(String, nullable=True, index=True)
    # step_name is a human-readable step identifier used by the UI timeline.
    step_name = Column(String, nullable=True, index=True)
    # elapsed_ms measures how long this row took (ms). Nullable for backward compatibility.
    elapsed_ms = Column(Float, nullable=True)
    result = Column(String, nullable=False)
    is_test = Column(Boolean, nullable=False, default=False)
    request_preview = Column(Text, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_excerpt = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    requested_by = Column(String, nullable=True)
    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    profile = relationship("EnforcementProfile", lazy='joined')

class Database():
    def __init__(self):
        self.database_url, self.database_location = self._resolve_database_configuration()
        self.engine = create_engine(self.database_url)

        # Create all tables in the engine
        Base.metadata.create_all(self.engine)
        self._run_schema_migrations()

        # Session factory: reuse for auxiliary sessions (e.g. audit logs) to avoid
        # add/commit on the main session while it may be inside flush/commit.
        self._sessionmaker = sessionmaker(bind=self.engine)
        self.session = self._sessionmaker()

    def _resolve_database_configuration(self):
        configured_url = os.getenv('DADM_DATABASE_URL')
        if configured_url:
            try:
                database_location = make_url(configured_url).render_as_string(hide_password=True)
            except Exception:
                database_location = 'configured via DADM_DATABASE_URL'
            logging.info("Using Domain-Manager database URL from DADM_DATABASE_URL: %s", database_location)
            return configured_url, database_location

        database_path_value = os.getenv('DADM_DATABASE_PATH')
        if database_path_value:
            database_path = Path(database_path_value).expanduser()
            if not database_path.is_absolute():
                database_path = Path(__file__).resolve().parent / database_path
        else:
            database_path = Path(__file__).resolve().parent / DEFAULT_DATABASE_FILENAME

        database_path.parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{database_path}"
        logging.info(f"Using Domain-Manager SQLite database at {database_path}")
        return database_url, str(database_path)

    def _run_schema_migrations(self):
        if self.engine.url.get_backend_name() != 'sqlite':
            return

        existing_tables = set(inspect(self.engine).get_table_names())
        if not existing_tables:
            return

        with self.engine.begin() as connection:
            for table_name, column_definitions in SQLITE_COLUMN_MIGRATIONS.items():
                if table_name not in existing_tables:
                    continue

                existing_columns = {
                    column['name']
                    for column in inspect(self.engine).get_columns(table_name)
                }

                for column_name, column_ddl in column_definitions.items():
                    if column_name in existing_columns:
                        continue

                    logging.info(
                        "Applying SQLite schema migration for %s.%s",
                        table_name,
                        column_name,
                    )
                    connection.execute(
                        text(
                            f'ALTER TABLE "{table_name}" '
                            f'ADD COLUMN "{column_name}" {column_ddl}'
                        )
                    )

    def createDevice(self, ip, mac, model, identifier, mudurl, mudfile, mitigation_actions, dsp_id, dsp,
                     name=None, type=None, manufacturer=None, status='active', edk=None,
                     discovered_threat_mud_urls=None, pilot_id=None):
        try:
            # Create and add new entry
            new_device = Device(ip=ip, mac=mac, model=model, identifier=identifier, mudurl=mudurl,
                                mudfile=mudfile, mitigation_actions=mitigation_actions, dsp_id=dsp_id, dsp=dsp,
                                name=name, type=type, manufacturer=manufacturer, status=status, edk=edk,
                                discovered_threat_mud_urls=discovered_threat_mud_urls, pilot_id=pilot_id)
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
                                 getattr(device, 'edk', None),
                                 getattr(device, 'discovered_threat_mud_urls', None),
                                 getattr(device, 'pilot_id', None))

    def createThreatFromObject(self, threat):
        return self.createThreat(threat.identifier, threat.threat_mud_url, threat.threat_mud_file,
                                 threat.mitigation_actions)

    def getDevice(self, identifier):
        """
        Resuelve un dispositivo por:
        1) device.identifier (UUID FDO u otro id lógico único)
        2) si no hay coincidencia y el parámetro es numérico, por clave primaria `device.id`
           (compatibilidad con clientes que usan /devices/<id> numérico).

        No se busca por dsp_id: no es único y provocaría mezclar dispositivos.
        """
        try:
            if identifier is None:
                return None
            s = str(identifier).strip()
            if not s:
                return None
            device = self.session.query(Device).filter_by(identifier=s).first()
            if device is not None:
                return device
            if s.isdigit():
                return self.session.query(Device).filter_by(id=int(s)).first()
            return None
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
            threat = self.session.query(Threat).filter_by(threat_mud_url=threat_mud_url).first()
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

    def getDevicesForUser(self, user_id):
        """Devices a non-admin user may see/manage, per their access rules.
        Empty list if the user has no rules (deny by default)."""
        try:
            rules = self.session.query(DeviceAccessRule).filter_by(user_id=user_id).all()
            idents = [r.match_value for r in rules if r.match_kind == 'device']
            manufs = [r.match_value for r in rules if r.match_kind == 'manufacturer']
            idsps = [r.match_value for r in rules if r.match_kind == 'idsp']
            if not (idents or manufs or idsps):
                return []
            conditions = []
            if idents:
                conditions.append(Device.identifier.in_(idents))
            if manufs:
                conditions.append(Device.manufacturer.in_(manufs))
            if idsps:
                conditions.append(Device.dsp_id.in_(idsps))
            return self.session.query(Device).filter(or_(*conditions)).all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving devices for user {user_id}", e)

    def userCanAccessDevice(self, user, device):
        """True if the user (current_user dict) may access the given Device object.
        Admins and superadmins can access everything."""
        if user and user.get('role') in ('admin', 'superadmin'):
            return True
        if not user or device is None:
            return False
        try:
            return self.session.query(DeviceAccessRule).filter_by(user_id=user['id']).filter(or_(
                and_(DeviceAccessRule.match_kind == 'device', DeviceAccessRule.match_value == device.identifier),
                and_(DeviceAccessRule.match_kind == 'manufacturer', DeviceAccessRule.match_value == device.manufacturer),
                and_(DeviceAccessRule.match_kind == 'idsp', DeviceAccessRule.match_value == device.dsp_id),
            )).first() is not None
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error checking device access for user {user.get('id')}", e)

    def getAccessRulesForUser(self, user_id):
        try:
            return self.session.query(DeviceAccessRule).filter_by(user_id=user_id).order_by(
                DeviceAccessRule.created_at.desc()).all()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving access rules for user {user_id}", e)

    def createAccessRule(self, user_id, match_kind, match_value):
        try:
            existing = self.session.query(DeviceAccessRule).filter_by(
                user_id=user_id, match_kind=match_kind, match_value=match_value).first()
            if existing is not None:
                return existing
            rule = DeviceAccessRule(user_id=user_id, match_kind=match_kind, match_value=match_value)
            self.session.add(rule)
            self.session.commit()
            return rule
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error creating access rule for user {user_id}", e)

    def deleteAccessRule(self, user_id, rule_id):
        try:
            rule = self.session.query(DeviceAccessRule).filter_by(id=rule_id, user_id=user_id).first()
            if rule is None:
                return False
            self.session.delete(rule)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error deleting access rule {rule_id} for user {user_id}", e)

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
                device_to_update.discovered_threat_mud_urls = device.discovered_threat_mud_urls
                device_to_update.pilot_id = getattr(device, 'pilot_id', None)
                device_to_update.enforcement_context = getattr(device, 'enforcement_context', None)
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

    def updateDeviceSecuritySnapshot(
        self,
        device_identifier,
        dsp,
        discovered_threat_mud_urls,
        *,
        mudurl=None,
        mudfile=None,
        update_mud=False,
        pilot_id=None,
    ):
        """Updates cached DSP, Threat MUD URLs, and optionally the resolved base MUD."""
        try:
            device_to_update = self.session.query(Device).filter_by(identifier=device_identifier).first()
            if device_to_update:
                device_to_update.dsp = dsp
                device_to_update.discovered_threat_mud_urls = discovered_threat_mud_urls
                if update_mud:
                    device_to_update.mudurl = mudurl
                    device_to_update.mudfile = mudfile
                if pilot_id:
                    device_to_update.pilot_id = pilot_id
                device_to_update.updated_at = datetime.now(timezone.utc)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error updating security snapshot for device {device_identifier}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error updating security snapshot for device {device_identifier}", e)

    def updateDeviceThreatSnapshot(self, device_identifier, dsp, discovered_threat_mud_urls):
        """Compatibility wrapper for older callers that only update DSP/Threat MUD data."""
        return self.updateDeviceSecuritySnapshot(
            device_identifier,
            dsp,
            discovered_threat_mud_urls,
            update_mud=False,
        )

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
                raw_id = device_to_delete.identifier
                did = str(raw_id).strip() if raw_id is not None else ""
                if did:
                    self.session.query(Policy).filter_by(device_id=did).delete(synchronize_session=False)
                    self.session.query(PolicyExecutionLog).filter_by(device_id=did).delete(synchronize_session=False)
                    self.session.query(Notification).filter_by(device_id=did).delete(synchronize_session=False)
                    self.session.query(DeviceEnforcementSecret).filter_by(device_identifier=did).delete(
                        synchronize_session=False
                    )
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
        # No usar device_id como model por defecto; si no hay name/model, model queda vacío
        return Device(ip=device_data.get('ip'), mac=device_data.get('mac'), model=device_data.get('model'),
                      identifier=device_data['device_id'], mudurl=None,
                      mudfile=None, mitigation_actions=None, dsp_id=device_data.get('idsp_id'), dsp=None,
                      name=device_data.get('name'), type=device_data.get('type'),
                      manufacturer=device_data.get('manufacturer'), status=device_data.get('status', 'active'),
                      edk=device_data.get('edk'),
                      discovered_threat_mud_urls=device_data.get('discovered_threat_mud_urls'),
                      pilot_id=device_data.get('pilot_id'))

    def upsertFeamCatalogSnapshot(self, snapshot: dict):
        try:
            serialized = json.dumps(snapshot)
            row = FeamCatalogSnapshot(snapshot_json=serialized)
            self.session.add(row)
            self.session.commit()
            return row
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError("Error upserting FEAM catalog snapshot", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError("Unexpected error upserting FEAM catalog snapshot", e)

    def getLatestFeamCatalogSnapshot(self):
        try:
            row = (
                self.session.query(FeamCatalogSnapshot)
                .order_by(FeamCatalogSnapshot.created_at.desc(), FeamCatalogSnapshot.id.desc())
                .first()
            )
            if row is None:
                return None
            return json.loads(row.snapshot_json)
        except SQLAlchemyError as e:
            raise DatabaseError("Error getting latest FEAM catalog snapshot", e)
        except Exception as e:
            raise DatabaseError("Unexpected error getting latest FEAM catalog snapshot", e)

    def upsertFeamPilotSyncState(self, pilot_id, status, error=None):
        try:
            row = self.session.query(FeamPilotSyncState).filter_by(pilot_id=pilot_id).first()
            if row is None:
                row = FeamPilotSyncState(
                    pilot_id=pilot_id,
                    last_sync_status=status,
                    last_error=error,
                    last_sync_at=datetime.now(timezone.utc),
                )
                self.session.add(row)
            else:
                row.last_sync_status = status
                row.last_error = error
                row.last_sync_at = datetime.now(timezone.utc)
                row.updated_at = datetime.now(timezone.utc)
            self.session.commit()
            return row
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error upserting FEAM pilot sync state for pilot {pilot_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error upserting FEAM pilot sync state for pilot {pilot_id}", e)

    def createPolicy(self, device_id, name, mspl_xml, policy_type='manual', source='user', status='pending', enforcement_status='pending', enforcement_blockers=None):
        """
        Crea una nueva política MSPL

        Args:
            device_id: El identifier del dispositivo
            name: Nombre descriptivo de la política
            mspl_xml: XML MSPL completo
            policy_type: Tipo de política ('manual', 'mud', etc.)
            source: Origen de la política ('user', 'idsp2', 'mud_file')
            status: Estado de la política ('pending', 'active', 'completed', 'failed')
            enforcement_status: Estado de enforcement ('pending', 'completed', 'failed', 'unknown', 'deferred')
            enforcement_blockers: JSON string con lista de requisitos faltantes (opcional)

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
                enforcement_blockers=enforcement_blockers,
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
                policy_to_update.enforcement_blockers = getattr(policy, 'enforcement_blockers', None)
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

    def createUser(self, email, password, role='user'):
        """
        Crea un nuevo usuario con password hasheado
        
        Args:
            email: Email del usuario (único)
            password: Password en texto plano (se hasheará)
            role: Rol del usuario ('user' o 'admin')
        
        Returns:
            User: El objeto User creado o None si el email ya existe
        """
        try:
            # Verificar si el usuario ya existe
            existing_user = self.session.query(User).filter_by(email=email).first()
            if existing_user:
                return None
            
            # Importar password_service aquí para evitar dependencia circular
            from core.auth.password_service import hash_password
            
            # Hash del password
            password_hash = hash_password(password)
            
            # Crear nuevo usuario
            new_user = User(
                email=email,
                password_hash=password_hash,
                role=role,
                is_active=True
            )
            self.session.add(new_user)
            self.session.commit()
            return new_user
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error creating user with email {email}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error creating user with email {email}", e)

    def getUser(self, email):
        """
        Obtiene un usuario por email
        
        Args:
            email: Email del usuario
        
        Returns:
            User: El objeto User o None si no existe
        """
        try:
            user = self.session.query(User).filter_by(email=email).first()
            return user
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving user with email {email}", e)
        except Exception as e:
            raise DatabaseError(f"Unexpected error retrieving user with email {email}", e)

    def getUserById(self, user_id):
        """
        Obtiene un usuario por ID
        
        Args:
            user_id: ID del usuario
        
        Returns:
            User: El objeto User o None si no existe
        """
        try:
            user = self.session.query(User).filter_by(id=user_id).first()
            return user
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving user with id {user_id}", e)
        except Exception as e:
            raise DatabaseError(f"Unexpected error retrieving user with id {user_id}", e)

    def getUsersPaginated(self, page=1, per_page=20, filters=None):
        """
        Obtiene usuarios con paginación optimizada
        
        Args:
            page: Número de página (empezando en 1)
            per_page: Items por página (máximo 100)
            filters: dict con {'role': 'admin', 'is_active': True, 'search': 'email'}
        
        Returns:
            tuple: (users_list, total_count)
        """
        try:
            # Validar per_page máximo
            if per_page > 100:
                per_page = 100
            
            # Construir query base
            query = self.session.query(User)
            
            # Aplicar filtros
            if filters:
                if filters.get('role'):
                    query = query.filter(User.role == filters['role'])
                if filters.get('is_active') is not None:
                    query = query.filter(User.is_active == filters['is_active'])
                if filters.get('search'):
                    search_term = f"%{filters['search']}%"
                    query = query.filter(User.email.ilike(search_term))
            
            # Conteo total (una query optimizada)
            total = query.count()
            
            # Paginación con offset y limit (una query optimizada)
            offset = (page - 1) * per_page
            users = query.order_by(User.created_at.desc()).offset(offset).limit(per_page).all()
            
            return users if users else [], total
        except SQLAlchemyError as e:
            raise DatabaseError("Error retrieving paginated users", e)
        except Exception as e:
            raise DatabaseError("Unexpected error retrieving paginated users", e)

    def getUsersCount(self, filters=None):
        """
        Obtiene el conteo total de usuarios con filtros
        
        Args:
            filters: dict con {'role': 'admin', 'is_active': True, 'search': 'email'}
        
        Returns:
            int: Número total de usuarios que cumplen los filtros
        """
        try:
            query = self.session.query(User)
            
            # Aplicar filtros (mismos que getUsersPaginated)
            if filters:
                if filters.get('role'):
                    query = query.filter(User.role == filters['role'])
                if filters.get('is_active') is not None:
                    query = query.filter(User.is_active == filters['is_active'])
                if filters.get('search'):
                    search_term = f"%{filters['search']}%"
                    query = query.filter(User.email.ilike(search_term))
            
            return query.count()
        except SQLAlchemyError as e:
            raise DatabaseError("Error counting users", e)
        except Exception as e:
            raise DatabaseError("Unexpected error counting users", e)

    def updateUserRole(self, user_id, new_role):
        """
        Actualiza el rol de un usuario
        
        Args:
            user_id: ID del usuario
            new_role: Nuevo rol ('user' o 'admin')
        
        Returns:
            bool: True si se actualizó correctamente, False si no existe
        """
        try:
            user_to_update = self.session.query(User).filter_by(id=user_id).first()
            if user_to_update:
                user_to_update.role = new_role
                user_to_update.updated_at = datetime.now(timezone.utc)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error updating user role for user {user_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error updating user role for user {user_id}", e)

    def updateUserLastLogin(self, user_id):
        """
        Actualiza el último login de un usuario
        
        Args:
            user_id: ID del usuario
        
        Returns:
            bool: True si se actualizó correctamente, False si no existe
        """
        try:
            user_to_update = self.session.query(User).filter_by(id=user_id).first()
            if user_to_update:
                user_to_update.last_login = datetime.now(timezone.utc)
                user_to_update.updated_at = datetime.now(timezone.utc)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error updating last login for user {user_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error updating last login for user {user_id}", e)

    def deleteUser(self, user_id):
        """
        Elimina un usuario permanentemente (hard delete)
        
        Args:
            user_id: ID del usuario
        
        Returns:
            bool: True si se eliminó correctamente, False si no existe
        """
        try:
            user_to_delete = self.session.query(User).filter_by(id=user_id).first()
            if user_to_delete:
                self.session.query(Notification).filter_by(user_id=user_id).delete(synchronize_session=False)
                self.session.query(TelegramLinkToken).filter_by(user_id=user_id).delete(synchronize_session=False)
                self.session.query(DeviceAccessRule).filter_by(user_id=user_id).delete(synchronize_session=False)
                self.session.delete(user_to_delete)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error deleting user with id {user_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error deleting user with id {user_id}", e)

    def activateUser(self, user_id):
        """
        Reactiva un usuario (is_active=True)
        
        Args:
            user_id: ID del usuario
        
        Returns:
            bool: True si se reactivó correctamente, False si no existe
        """
        try:
            user_to_activate = self.session.query(User).filter_by(id=user_id).first()
            if user_to_activate:
                user_to_activate.is_active = True
                user_to_activate.updated_at = datetime.now(timezone.utc)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error activating user with id {user_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error activating user with id {user_id}", e)

    def deactivateUser(self, user_id):
        """
        Desactiva un usuario (is_active=False)
        
        Args:
            user_id: ID del usuario
        
        Returns:
            bool: True si se desactivó correctamente, False si no existe
        """
        try:
            user_to_deactivate = self.session.query(User).filter_by(id=user_id).first()
            if user_to_deactivate:
                user_to_deactivate.is_active = False
                user_to_deactivate.updated_at = datetime.now(timezone.utc)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error deactivating user with id {user_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error deactivating user with id {user_id}", e)

    # ==================== NOTIFICATIONS & TELEGRAM ====================

    def getUsersEligibleForPrerequisiteNotifications(self):
        """Active users who should receive prerequisite alerts (in-app and/or Telegram)."""
        try:
            return (
                self.session.query(User)
                .filter(
                    User.is_active.is_(True),
                    or_(
                        User.in_app_notifications_enabled.is_(True),
                        and_(
                            User.telegram_enabled.is_(True),
                            User.telegram_chat_id.isnot(None),
                            User.telegram_chat_id != '',
                        ),
                    ),
                )
                .all()
            )
        except SQLAlchemyError as e:
            raise DatabaseError("Error listing users for notifications", e)
        except Exception as e:
            raise DatabaseError("Unexpected error listing users for notifications", e)

    def getUsersEligibleForAdminNotifications(self):
        """Active admin/superadmin users who should receive system alerts (in-app and/or Telegram)."""
        try:
            return (
                self.session.query(User)
                .filter(
                    User.is_active.is_(True),
                    User.role.in_(('admin', 'superadmin')),
                    or_(
                        User.in_app_notifications_enabled.is_(True),
                        and_(
                            User.telegram_enabled.is_(True),
                            User.telegram_chat_id.isnot(None),
                            User.telegram_chat_id != '',
                        ),
                    ),
                )
                .all()
            )
        except SQLAlchemyError as e:
            raise DatabaseError("Error listing admin users for notifications", e)
        except Exception as e:
            raise DatabaseError("Unexpected error listing admin users for notifications", e)

    def getNotificationByDedupKey(self, deduplication_key):
        try:
            return (
                self.session.query(Notification)
                .filter_by(deduplication_key=deduplication_key)
                .first()
            )
        except SQLAlchemyError as e:
            raise DatabaseError("Error fetching notification by dedup key", e)
        except Exception as e:
            raise DatabaseError("Unexpected error fetching notification by dedup key", e)

    def createNotification(
        self,
        *,
        user_id,
        device_id,
        notification_type,
        language,
        message,
        deduplication_key,
        policy_id=None,
        threat_id=None,
        mitigation_id=None,
        threat_mud_url=None,
        status='pending',
    ):
        try:
            row = Notification(
                user_id=user_id,
                device_id=device_id,
                policy_id=policy_id,
                threat_id=threat_id,
                mitigation_id=mitigation_id,
                threat_mud_url=threat_mud_url,
                notification_type=notification_type,
                status=status,
                language=language or 'es',
                message=message,
                deduplication_key=deduplication_key,
            )
            self.session.add(row)
            self.session.commit()
            return row
        except IntegrityError:
            self.session.rollback()
            return None
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError("Error creating notification", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError("Unexpected error creating notification", e)

    def getNotificationById(self, notification_id):
        try:
            return self.session.query(Notification).filter_by(id=notification_id).first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving notification {notification_id}", e)
        except Exception as e:
            raise DatabaseError(f"Unexpected error retrieving notification {notification_id}", e)

    def getNotificationsForUser(self, user_id, page=1, per_page=20, status=None, read_state=None):
        try:
            if per_page > 100:
                per_page = 100
            q = self.session.query(Notification).filter(Notification.user_id == user_id)
            if status:
                q = q.filter(Notification.status == status)
            if read_state == 'unread':
                q = q.filter(Notification.read_at.is_(None))
            elif read_state == 'read':
                q = q.filter(Notification.read_at.isnot(None))
            total = q.count()
            offset = (page - 1) * per_page
            rows = (
                q.order_by(Notification.created_at.desc())
                .offset(offset)
                .limit(per_page)
                .all()
            )
            return rows if rows else [], total
        except SQLAlchemyError as e:
            raise DatabaseError("Error listing notifications", e)
        except Exception as e:
            raise DatabaseError("Unexpected error listing notifications", e)

    def countUnreadNotificationsForUser(self, user_id):
        try:
            n = (
                self.session.query(Notification)
                .filter(Notification.user_id == user_id, Notification.read_at.is_(None))
                .count()
            )
            return int(n or 0)
        except SQLAlchemyError as e:
            raise DatabaseError("Error counting unread notifications", e)
        except Exception as e:
            raise DatabaseError("Unexpected error counting unread notifications", e)

    def getPendingNotifications(self, limit=50):
        try:
            return (
                self.session.query(Notification)
                .filter(Notification.status == 'pending')
                .order_by(Notification.created_at.asc())
                .limit(limit)
                .all()
            )
        except SQLAlchemyError as e:
            raise DatabaseError("Error listing pending notifications", e)
        except Exception as e:
            raise DatabaseError("Unexpected error listing pending notifications", e)

    def updateNotificationFields(self, notification_id, **kwargs):
        try:
            row = self.session.query(Notification).filter_by(id=notification_id).first()
            if not row:
                return False
            for k, v in kwargs.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error updating notification {notification_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error updating notification {notification_id}", e)

    def markNotificationRead(self, notification_id, user_id):
        try:
            row = (
                self.session.query(Notification)
                .filter(Notification.id == notification_id, Notification.user_id == user_id)
                .first()
            )
            if not row:
                return False
            row.read_at = datetime.now(timezone.utc)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError("Error marking notification read", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError("Unexpected error marking notification read", e)

    def markAllNotificationsRead(self, user_id):
        try:
            now = datetime.now(timezone.utc)
            updated = (
                self.session.query(Notification)
                .filter(Notification.user_id == user_id, Notification.read_at.is_(None))
                .update({Notification.read_at: now}, synchronize_session=False)
            )
            self.session.commit()
            return int(updated or 0)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError("Error marking all notifications read", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError("Unexpected error marking all notifications read", e)

    def createTelegramLinkToken(self, token, user_id, expires_at):
        try:
            row = TelegramLinkToken(token=token, user_id=user_id, expires_at=expires_at, used=False)
            self.session.add(row)
            self.session.commit()
            return row
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError("Error creating telegram link token", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError("Unexpected error creating telegram link token", e)

    def getValidTelegramLinkToken(self, token):
        try:
            now = datetime.now(timezone.utc)
            row = self.session.query(TelegramLinkToken).filter_by(token=token, used=False).first()
            if row is None:
                return None
            exp = row.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < now:
                return None
            return row
        except SQLAlchemyError as e:
            raise DatabaseError("Error fetching telegram link token", e)
        except Exception as e:
            raise DatabaseError("Unexpected error fetching telegram link token", e)

    def markTelegramLinkTokenUsed(self, token_id):
        try:
            row = self.session.query(TelegramLinkToken).filter_by(id=token_id).first()
            if row:
                row.used = True
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError("Error marking telegram token used", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError("Unexpected error marking telegram token used", e)

    def updateUserTelegramAndSettings(
        self,
        user_id,
        *,
        telegram_chat_id=None,
        telegram_enabled=None,
        language=None,
        in_app_notifications_enabled=None,
        clear_telegram=False,
    ):
        try:
            u = self.session.query(User).filter_by(id=user_id).first()
            if not u:
                return False
            if clear_telegram:
                u.telegram_chat_id = None
                u.telegram_enabled = False
            if telegram_chat_id is not None:
                u.telegram_chat_id = telegram_chat_id
            if telegram_enabled is not None:
                u.telegram_enabled = bool(telegram_enabled)
            if language is not None:
                u.language = language
            if in_app_notifications_enabled is not None:
                u.in_app_notifications_enabled = bool(in_app_notifications_enabled)
            u.updated_at = datetime.now(timezone.utc)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error updating user notification settings {user_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error updating user notification settings {user_id}", e)

    # ==================== ENFORCEMENT CONFIGURATION ====================
    def listEnforcementProfiles(self, include_inactive=True):
        try:
            query = self.session.query(EnforcementProfile)
            if not include_inactive:
                query = query.filter(EnforcementProfile.is_active.is_(True))
            return query.order_by(EnforcementProfile.id.asc()).all()
        except SQLAlchemyError as e:
            raise DatabaseError("Error listing enforcement profiles", e)
        except Exception as e:
            raise DatabaseError("Unexpected error listing enforcement profiles", e)

    def getEnforcementProfile(self, profile_id):
        try:
            return self.session.query(EnforcementProfile).filter_by(id=profile_id).first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving enforcement profile with id {profile_id}", e)
        except Exception as e:
            raise DatabaseError(f"Unexpected error retrieving enforcement profile with id {profile_id}", e)

    def getEnforcementProfileByName(self, name):
        try:
            return self.session.query(EnforcementProfile).filter_by(name=name).first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving enforcement profile with name {name}", e)
        except Exception as e:
            raise DatabaseError(f"Unexpected error retrieving enforcement profile with name {name}", e)

    def getDefaultEnforcementProfile(self):
        try:
            return (
                self.session.query(EnforcementProfile)
                .filter(
                    EnforcementProfile.is_active.is_(True),
                    EnforcementProfile.is_default.is_(True)
                )
                .order_by(EnforcementProfile.id.asc())
                .first()
            )
        except SQLAlchemyError as e:
            raise DatabaseError("Error retrieving default enforcement profile", e)
        except Exception as e:
            raise DatabaseError("Unexpected error retrieving default enforcement profile", e)

    def getActiveEnforcementProfiles(self):
        try:
            return (
                self.session.query(EnforcementProfile)
                .filter(EnforcementProfile.is_active.is_(True))
                .order_by(EnforcementProfile.id.asc())
                .all()
            )
        except SQLAlchemyError as e:
            raise DatabaseError("Error retrieving active enforcement profiles", e)
        except Exception as e:
            raise DatabaseError("Unexpected error retrieving active enforcement profiles", e)

    def createEnforcementProfile(self, **data):
        try:
            profile = EnforcementProfile(**data)
            self.session.add(profile)
            self.session.commit()
            return profile
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError("Error creating enforcement profile", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError("Unexpected error creating enforcement profile", e)

    def updateEnforcementProfile(self, profile_id, **data):
        try:
            profile = self.session.query(EnforcementProfile).filter_by(id=profile_id).first()
            if profile is None:
                return None
            for key, value in data.items():
                setattr(profile, key, value)
            profile.updated_at = datetime.now(timezone.utc)
            self.session.commit()
            return profile
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error updating enforcement profile with id {profile_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error updating enforcement profile with id {profile_id}", e)

    def clearDefaultEnforcementProfiles(self, exclude_profile_id=None):
        try:
            query = self.session.query(EnforcementProfile).filter(EnforcementProfile.is_default.is_(True))
            if exclude_profile_id is not None:
                query = query.filter(EnforcementProfile.id != exclude_profile_id)
            rows = query.all()
            for row in rows:
                row.is_default = False
                row.updated_at = datetime.now(timezone.utc)
            self.session.commit()
            return len(rows)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError("Error clearing default enforcement profiles", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError("Unexpected error clearing default enforcement profiles", e)

    def deleteEnforcementProfile(self, profile_id):
        try:
            profile = self.session.query(EnforcementProfile).filter_by(id=profile_id).first()
            if profile is None:
                return False
            self.session.delete(profile)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error deleting enforcement profile with id {profile_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error deleting enforcement profile with id {profile_id}", e)

    def listEnforcementMappings(self, include_inactive=True):
        try:
            query = self.session.query(EnforcementMapping)
            if not include_inactive:
                query = query.filter(EnforcementMapping.is_active.is_(True))
            return query.order_by(EnforcementMapping.priority.asc(), EnforcementMapping.id.asc()).all()
        except SQLAlchemyError as e:
            raise DatabaseError("Error listing enforcement mappings", e)
        except Exception as e:
            raise DatabaseError("Unexpected error listing enforcement mappings", e)

    def getEnforcementMapping(self, mapping_id):
        try:
            return self.session.query(EnforcementMapping).filter_by(id=mapping_id).first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving enforcement mapping with id {mapping_id}", e)
        except Exception as e:
            raise DatabaseError(f"Unexpected error retrieving enforcement mapping with id {mapping_id}", e)

    def findEnforcementMappings(self, match_kind, match_value):
        try:
            return (
                self.session.query(EnforcementMapping)
                .filter(
                    EnforcementMapping.is_active.is_(True),
                    EnforcementMapping.match_kind == match_kind,
                    EnforcementMapping.match_value == match_value
                )
                .order_by(EnforcementMapping.priority.asc(), EnforcementMapping.id.asc())
                .all()
            )
        except SQLAlchemyError as e:
            raise DatabaseError("Error querying enforcement mappings", e)
        except Exception as e:
            raise DatabaseError("Unexpected error querying enforcement mappings", e)

    def createEnforcementMapping(self, **data):
        try:
            mapping = EnforcementMapping(**data)
            self.session.add(mapping)
            self.session.commit()
            return mapping
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError("Error creating enforcement mapping", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError("Unexpected error creating enforcement mapping", e)

    def updateEnforcementMapping(self, mapping_id, **data):
        try:
            mapping = self.session.query(EnforcementMapping).filter_by(id=mapping_id).first()
            if mapping is None:
                return None
            for key, value in data.items():
                setattr(mapping, key, value)
            mapping.updated_at = datetime.now(timezone.utc)
            self.session.commit()
            return mapping
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error updating enforcement mapping with id {mapping_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error updating enforcement mapping with id {mapping_id}", e)

    def deleteEnforcementMapping(self, mapping_id):
        try:
            mapping = self.session.query(EnforcementMapping).filter_by(id=mapping_id).first()
            if mapping is None:
                return False
            self.session.delete(mapping)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error deleting enforcement mapping with id {mapping_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error deleting enforcement mapping with id {mapping_id}", e)

    def listEnforcementSecrets(self):
        try:
            return (
                self.session.query(EnforcementSecret)
                .order_by(EnforcementSecret.id.asc())
                .all()
            )
        except SQLAlchemyError as e:
            raise DatabaseError("Error listing enforcement secrets", e)
        except Exception as e:
            raise DatabaseError("Unexpected error listing enforcement secrets", e)

    def getEnforcementSecret(self, secret_id):
        try:
            return self.session.query(EnforcementSecret).filter_by(id=secret_id).first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving enforcement secret with id {secret_id}", e)
        except Exception as e:
            raise DatabaseError(f"Unexpected error retrieving enforcement secret with id {secret_id}", e)

    def getEnforcementSecretByName(self, name):
        try:
            return self.session.query(EnforcementSecret).filter_by(name=name).first()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Error retrieving enforcement secret with name {name}", e)
        except Exception as e:
            raise DatabaseError(f"Unexpected error retrieving enforcement secret with name {name}", e)

    def createEnforcementSecret(self, **data):
        try:
            secret = EnforcementSecret(**data)
            self.session.add(secret)
            self.session.commit()
            return secret
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError("Error creating enforcement secret", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError("Unexpected error creating enforcement secret", e)

    def updateEnforcementSecret(self, secret_id, **data):
        try:
            secret = self.session.query(EnforcementSecret).filter_by(id=secret_id).first()
            if secret is None:
                return None
            for key, value in data.items():
                setattr(secret, key, value)
            secret.updated_at = datetime.now(timezone.utc)
            self.session.commit()
            return secret
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error updating enforcement secret with id {secret_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error updating enforcement secret with id {secret_id}", e)

    def deleteEnforcementSecret(self, secret_id):
        try:
            secret = self.session.query(EnforcementSecret).filter_by(id=secret_id).first()
            if secret is None:
                return False
            self.session.delete(secret)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError(f"Error deleting enforcement secret with id {secret_id}", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Unexpected error deleting enforcement secret with id {secret_id}", e)

    def getDeviceEnforcementSecret(self, device_identifier, purpose="bearer_token"):
        try:
            return (
                self.session.query(DeviceEnforcementSecret)
                .filter_by(device_identifier=str(device_identifier), purpose=purpose)
                .first()
            )
        except SQLAlchemyError as e:
            raise DatabaseError("Error getting device enforcement secret", e)
        except Exception as e:
            raise DatabaseError("Unexpected error getting device enforcement secret", e)

    def upsertDeviceEnforcementSecret(self, device_identifier, purpose, *, ciphertext, nonce, key_version):
        try:
            did = str(device_identifier)
            existing = self.getDeviceEnforcementSecret(did, purpose=purpose)
            if existing is None:
                row = DeviceEnforcementSecret(
                    device_identifier=did,
                    purpose=purpose,
                    ciphertext=ciphertext,
                    nonce=nonce,
                    key_version=key_version,
                )
                self.session.add(row)
            else:
                existing.ciphertext = ciphertext
                existing.nonce = nonce
                existing.key_version = key_version
                existing.updated_at = datetime.now(timezone.utc)
            self.session.commit()
            return self.getDeviceEnforcementSecret(did, purpose=purpose)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError("Error upserting device enforcement secret", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError("Unexpected error upserting device enforcement secret", e)

    def deleteDeviceEnforcementSecret(self, device_identifier, purpose="bearer_token"):
        try:
            row = self.getDeviceEnforcementSecret(device_identifier, purpose=purpose)
            if row is None:
                return False
            self.session.delete(row)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError("Error deleting device enforcement secret", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError("Unexpected error deleting device enforcement secret", e)

    def createPolicyExecutionLog(self, **data):
        log_session = self._sessionmaker()
        try:
            log_entry = PolicyExecutionLog(**data)
            log_session.add(log_entry)
            log_session.commit()
            return log_entry
        except SQLAlchemyError as e:
            log_session.rollback()
            raise DatabaseError("Error creating policy execution log", e)
        except Exception as e:
            log_session.rollback()
            raise DatabaseError("Unexpected error creating policy execution log", e)
        finally:
            log_session.close()

    def listPolicyExecutionLogs(
        self,
        *,
        from_date=None,
        to_date=None,
        result=None,
        device_id=None,
        is_test=None,
        profile_id=None,
        limit=200
    ):
        try:
            query = self.session.query(PolicyExecutionLog)
            if from_date is not None:
                query = query.filter(PolicyExecutionLog.executed_at >= from_date)
            if to_date is not None:
                query = query.filter(PolicyExecutionLog.executed_at <= to_date)
            if result:
                query = query.filter(PolicyExecutionLog.result == result)
            if device_id:
                query = query.filter(PolicyExecutionLog.device_id == device_id)
            if is_test is not None:
                query = query.filter(PolicyExecutionLog.is_test.is_(is_test))
            if profile_id is not None:
                query = query.filter(PolicyExecutionLog.profile_id == profile_id)
            if limit > 1000:
                limit = 1000
            if limit < 1:
                limit = 200
            return (
                query
                .order_by(PolicyExecutionLog.executed_at.desc(), PolicyExecutionLog.id.desc())
                .limit(limit)
                .all()
            )
        except SQLAlchemyError as e:
            raise DatabaseError("Error listing policy execution logs", e)
        except Exception as e:
            raise DatabaseError("Unexpected error listing policy execution logs", e)

    def purgePolicyExecutionLogsOlderThanDays(self, days=3):
        """
        Elimina logs de policy_execution_log más antiguos que N días.

        Args:
            days: Número de días de retención.

        Returns:
            int: Cantidad de filas eliminadas.
        """
        try:
            retention_days = int(days)
            if retention_days < 0:
                retention_days = 0
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
            deleted_rows = (
                self.session.query(PolicyExecutionLog)
                .filter(PolicyExecutionLog.executed_at < cutoff)
                .delete(synchronize_session=False)
            )
            self.session.commit()
            return int(deleted_rows or 0)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise DatabaseError("Error purging old policy execution logs", e)
        except Exception as e:
            self.session.rollback()
            raise DatabaseError("Unexpected error purging old policy execution logs", e)

    def vacuumSqlite(self):
        """
        Ejecuta VACUUM solo cuando el backend es SQLite.
        """
        try:
            if self.engine.url.get_backend_name() != 'sqlite':
                return False
            with self.engine.begin() as connection:
                connection.execute(text("VACUUM"))
            return True
        except SQLAlchemyError as e:
            raise DatabaseError("Error running SQLite VACUUM", e)
        except Exception as e:
            raise DatabaseError("Unexpected error running SQLite VACUUM", e)

    def verifyPassword(self, user, password):
        """
        Verifica un password contra el hash almacenado
        
        Args:
            user: Objeto User
            password: Password en texto plano
        
        Returns:
            bool: True si el password es correcto, False en caso contrario
        """
        try:
            from core.auth.password_service import verify_password
            return verify_password(password, user.password_hash)
        except Exception as e:
            raise DatabaseError(f"Error verifying password for user {user.id}", e)

    def printDevice(self, device):
        print(
            "IP: " + str(device.ip) + ", MAC: " + str(device.mac) + ", model: " + str(device.model) + ", identifier: " + str(device.identifier) + ", mudurl: " + str(device.mudurl) + ", mudfile: " + str(device.mudfile) + ", mitigation_actions: " + str(device.mitigation_actions) + ", dsp_id: " + str(device.dsp_id) + ", dsp: " + str(device.dsp) + ", discovered_threat_mud_urls: " + str(device.discovered_threat_mud_urls))
        
        return "IP: " + str(device.ip) + ", MAC: " + str(device.mac) + ", model: " + str(device.model) + ", identifier: " + str(device.identifier) + ", mudurl: " + str(device.mudurl) + ", mudfile: " + str(device.mudfile) + ", mitigation_actions: " + str(device.mitigation_actions) + ", dsp_id: " + str(device.dsp_id) + ", dsp: " + str(device.dsp) + ", discovered_threat_mud_urls: " + str(device.discovered_threat_mud_urls)
