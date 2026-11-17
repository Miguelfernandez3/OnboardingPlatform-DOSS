# services/device_service.py
"""
Service for handling device-related logic.
Consolidates register_dsp(), printAllDevices() and other device operations.
"""
from typing import Any, Dict, List, Optional
import logging
import json
import os
import threading
import time
import uuid
from services.mud_service import MUDService
from services.feam_service import FEAMService
from services.dsp_metadata import extract_device_identity_from_gendsp
from services.policy_enforcement_service import EnforcementPrerequisitesError, PolicyEnforcementService
from services.policy_service import PolicyService
from services.threat_service import ThreatService
from services.mitigation_service import MitigationService
from services.notifications.service import NotificationService
from datetime import datetime, timezone


class DeviceRegistrationError(Exception):
    """Structured error used for DSP-based device registration failures."""

    def __init__(self, message: str, code: str = 'CREATE_FAILED', status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class DeviceService:
    """
    Service for device-related operations.
    """
    def __init__(self, db, mud_service: MUDService, feam_service: FEAMService):
        """
        Args:
            db: Database instance
            mud_service: Service for MUD operations
            feam_service: Service for FEAM operations
        """
        self.db = db
        self.mud_service = mud_service
        self.feam_service = feam_service
        self.policy_service = None
        self.policy_enforcement_service = None
        self.mitigation_service = None
        self.db_factory = None
        self._poll_interval_seconds = 20
        self._poll_stop_event = threading.Event()
        self._poll_thread = None

    def set_policy_services(self, policy_service, policy_enforcement_service):
        """Injects optional policy services used for post-registration auto-enforcement."""
        self.policy_service = policy_service
        self.policy_enforcement_service = policy_enforcement_service

    def set_mitigation_service(self, mitigation_service):
        """Injects MitigationService for proactive prerequisite notifications after DSP register."""
        self.mitigation_service = mitigation_service

    def configure_polling(self, *, poll_interval_seconds: int = 5, db_factory=None):
        """Configures backend DSP threat polling settings."""
        self._poll_interval_seconds = max(1, int(poll_interval_seconds or 5))
        self.db_factory = db_factory

    @staticmethod
    def _serialize_discovered_threat_urls(urls: List[str]) -> Optional[str]:
        cleaned = []
        for url in urls or []:
            text = str(url or "").strip()
            if text and text not in cleaned:
                cleaned.append(text)
        return json.dumps(cleaned) if cleaned else None

    def _record_onboarding_step(
        self,
        *,
        device_id: str,
        correlation_id: str,
        step_name: str,
        result: str,
        elapsed_ms: Optional[float],
        error_message: Optional[str] = None,
    ):
        """
        Persists one row in policy_execution_log used as onboarding timeline source.
        """
        if self.policy_enforcement_service is not None:
            self.policy_enforcement_service.record_execution(
                device_id=device_id,
                policy_id=None,
                policy_name=step_name,
                profile_id=None,
                result=result,
                run_mode="onboarding",
                is_test=False,
                event_type="onboarding_step",
                correlation_id=correlation_id,
                step_name=step_name,
                elapsed_ms=elapsed_ms,
                error_message=error_message,
            )
            return

        # Fallback (defensive): write directly to DB if enforcement service isn't injected.
        try:
            self.db.createPolicyExecutionLog(
                device_id=device_id,
                policy_id=None,
                policy_name=step_name,
                profile_id=None,
                run_mode="onboarding",
                result=result,
                is_test=False,
                event_type="onboarding_step",
                correlation_id=correlation_id,
                step_name=step_name,
                elapsed_ms=elapsed_ms,
                error_message=error_message,
                request_preview=None,
                response_status=None,
                response_excerpt=None,
                requested_by=None,
            )
        except Exception:
            logging.exception("Failed to persist onboarding timeline log")

    def _build_polling_services(self, active_db):
        """
        Builds service instances bound to the poller's DB session.
        HTTP clients are reused, but DB-backed services must not use the main thread session.
        """
        feam_service = FEAMService(self.feam_service.feam_client, active_db)
        try:
            feam_service._catalog_cache = dict(getattr(self.feam_service, "_catalog_cache", {}) or {})
        except Exception:
            pass

        legacy_enforcer = (
            getattr(self.policy_enforcement_service, "legacy_enforcer", None)
            or (lambda _mspl_xml, _device: None)
        )
        policy_enforcement_service = PolicyEnforcementService(active_db, legacy_enforcer)
        policy_service = PolicyService(active_db, policy_enforcement_service)

        threat_service = None
        mitigation_service = None
        if self.mitigation_service is not None and getattr(self.mitigation_service, "threat_service", None):
            threat_client = self.mitigation_service.threat_service.threat_mud_client
            threat_service = ThreatService(threat_client, active_db)
            mitigation_service = MitigationService(
                active_db,
                threat_service,
                policy_enforcement_service,
            )

        return {
            "feam": feam_service,
            "policy": policy_service,
            "policy_enforcement": policy_enforcement_service,
            "threat": threat_service,
            "mitigation": mitigation_service,
        }

    def _refresh_device_threat_snapshot(self, device_identifier: str, dsp_id: str, *, db_override=None) -> bool:
        """Compatibility helper; the full poller now refreshes MUD/policy state too."""
        active_db = db_override or self.db
        if not device_identifier or not dsp_id:
            return False
        services = self._build_polling_services(active_db) if active_db is not self.db else None
        device = active_db.getDevice(device_identifier)
        if device is None:
            return False
        return self._sync_device_security_snapshot(
            device,
            active_db=active_db,
            services=services,
            dsp_snapshot_cache={},
        )

    def _current_mud_policy_hashes(self, device, policy_service: PolicyService) -> Optional[set[str]]:
        if not getattr(device, "mudfile", None):
            return set()
        try:
            mud_json = json.loads(device.mudfile)
            candidate_policies = policy_service.translate_mud_json_to_policies(
                mud_json,
                device_id=getattr(device, "identifier", "preview"),
            )
            return {
                policy_service._hash_mspl(policy.get("msplXml"))
                for policy in candidate_policies
                if policy.get("msplXml")
            }
        except Exception as exc:
            logging.warning(
                "[DSP security poll] Cannot translate current MUD for superseded check on device=%s: %s",
                getattr(device, "identifier", None),
                exc,
                exc_info=True,
            )
            return None

    def _mark_superseded_mud_policies(self, device, *, active_db, policy_service: PolicyService) -> None:
        current_hashes = self._current_mud_policy_hashes(device, policy_service)
        if current_hashes is None:
            return
        device_id = getattr(device, "identifier", None)
        if not device_id:
            return
        for policy in active_db.getPoliciesByDevice(device_id):
            source_value = str(getattr(policy, "source", "") or "").strip().lower()
            if source_value not in {"mud", "mud_file"}:
                continue
            policy_hash = policy_service._hash_mspl(getattr(policy, "mspl_xml", None))
            if policy_hash in current_hashes:
                continue
            state_values = {
                str(getattr(policy, "status", "") or "").strip().lower(),
                str(getattr(policy, "enforcement_status", "") or "").strip().lower(),
            }
            if "superseded" in state_values:
                continue
            policy.status = "superseded"
            policy.enforcement_status = "superseded"
            policy.enforcement_blockers = json.dumps(
                {"reason": "superseded_by_current_mud"},
                ensure_ascii=True,
            )
            active_db.updatePolicy(policy)
            logging.info(
                "[DSP security poll] Marked MUD policy superseded: device=%s policy_id=%s",
                device_id,
                getattr(policy, "id", None),
            )

    def _import_threat_muds_and_notify(self, device, *, services) -> None:
        threat_service = services.get("threat") if services else None
        mitigation_service = services.get("mitigation") if services else None
        if threat_service is not None:
            try:
                threat_service.get_matching_threats(device)
            except Exception as exc:
                logging.warning(
                    "[DSP security poll] Threat MUD import/match failed for device=%s: %s",
                    getattr(device, "identifier", None),
                    exc,
                    exc_info=True,
                )
        if mitigation_service is not None:
            self._notify_unapplied_mitigation_gaps_if_any(
                device,
                db_override=services.get("db"),
                mitigation_service=mitigation_service,
            )

    def _sync_device_security_snapshot(self, device, *, active_db, services, dsp_snapshot_cache) -> bool:
        dsp_id = getattr(device, "dsp_id", None)
        device_identifier = getattr(device, "identifier", None)
        if not dsp_id or not device_identifier:
            return False

        feam_service = services.get("feam") if services else self.feam_service
        policy_service = services.get("policy") if services else self.policy_service
        policy_enforcement_service = (
            services.get("policy_enforcement") if services else self.policy_enforcement_service
        )

        cached_snapshot = dsp_snapshot_cache.get(dsp_id)
        if cached_snapshot is None:
            dsp_payload = self.get_gendsp_from_idsp(dsp_id, feam_service=feam_service)
            discovered_urls = self.mud_service.get_threat_mud_urls_from_dsp(dsp_payload)
            cached_snapshot = {
                "dsp": dsp_payload,
                "urls": self._serialize_discovered_threat_urls(discovered_urls),
                "discovered_urls": discovered_urls,
                "pilot_id": feam_service.resolve_pilot_from_dsp(dsp_payload),
            }
            dsp_snapshot_cache[dsp_id] = cached_snapshot
            logging.info(
                "[DSP security poll] Refreshed source snapshot for dsp_id=%s (will be reused for matching devices)",
                dsp_id,
            )

        old_dsp = getattr(device, "dsp", None)
        old_urls = getattr(device, "discovered_threat_mud_urls", None)
        old_mudurl = getattr(device, "mudurl", None)
        old_mudfile = getattr(device, "mudfile", None)

        dsp_changed = cached_snapshot["dsp"] != old_dsp
        threat_urls_changed = cached_snapshot["urls"] != old_urls
        should_check_mud = dsp_changed or not old_mudurl or not old_mudfile
        update_mud = False
        new_mudurl = old_mudurl
        new_mudfile = old_mudfile

        if should_check_mud:
            try:
                resolved_mudurl = self.mud_service.get_mud_url_from_dsp(cached_snapshot["dsp"])
            except Exception as exc:
                logging.warning(
                    "[DSP security poll] MUD URL resolution failed for device=%s dsp_id=%s: %s",
                    device_identifier,
                    dsp_id,
                    exc,
                    exc_info=True,
                )
                resolved_mudurl = None

            if resolved_mudurl:
                should_fetch_mud = dsp_changed or resolved_mudurl != old_mudurl or not old_mudfile
                if should_fetch_mud:
                    try:
                        ret = self.mud_service.mud_manager_client.get_mud_file(
                            resolved_mudurl,
                            device_identifier,
                        )
                    except Exception as exc:
                        logging.warning(
                            "[DSP security poll] MUD download failed for device=%s mudurl=%s: %s",
                            device_identifier,
                            resolved_mudurl,
                            exc,
                            exc_info=True,
                        )
                        ret = None
                    if ret and ret.get("mudfile"):
                        candidate_mudurl = ret.get("mudurl") or resolved_mudurl
                        candidate_mudfile = ret.get("mudfile")
                        update_mud = candidate_mudurl != old_mudurl or candidate_mudfile != old_mudfile
                        new_mudurl = candidate_mudurl
                        new_mudfile = candidate_mudfile
                    else:
                        logging.warning(
                            "[DSP security poll] Keeping previous MUD for device=%s because download returned no file",
                            device_identifier,
                        )

        pilot_id = cached_snapshot.get("pilot_id")
        pilot_changed = bool(pilot_id) and pilot_id != getattr(device, "pilot_id", None)
        security_changed = dsp_changed or threat_urls_changed or update_mud or pilot_changed
        if not security_changed:
            return False

        active_db.updateDeviceSecuritySnapshot(
            device_identifier,
            cached_snapshot["dsp"],
            cached_snapshot["urls"],
            mudurl=new_mudurl,
            mudfile=new_mudfile,
            update_mud=update_mud,
            pilot_id=pilot_id,
        )
        updated_device = active_db.getDevice(device_identifier)
        if updated_device is None:
            return True

        logging.info(
            "[DSP security poll] Updated device=%s dsp_id=%s dspChanged=%s mudChanged=%s threatUrlsChanged=%s",
            device_identifier,
            dsp_id,
            dsp_changed,
            update_mud,
            threat_urls_changed,
        )

        if update_mud and policy_service is not None and policy_enforcement_service is not None:
            self._mark_superseded_mud_policies(
                updated_device,
                active_db=active_db,
                policy_service=policy_service,
            )
            self._auto_enforce_mud_policies(
                updated_device,
                correlation_id=uuid.uuid4().hex,
                db_override=active_db,
                policy_service=policy_service,
                policy_enforcement_service=policy_enforcement_service,
            )

        if threat_urls_changed or update_mud:
            if services is not None:
                services["db"] = active_db
            self._import_threat_muds_and_notify(updated_device, services=services)

        return True

    def poll_dsp_threat_updates_once(self, *, db_override=None):
        """Refreshes DSP, base MUD, MUD policies, and discovered Threat MUD URLs."""
        active_db = db_override or self.db
        services = self._build_polling_services(active_db) if active_db is not self.db else None
        devices = active_db.getAllDevices()
        dsp_snapshot_cache: Dict[str, Dict[str, Any]] = {}
        for device in devices:
            device_identifier = getattr(device, "identifier", None)
            dsp_id = getattr(device, "dsp_id", None)
            if not dsp_id or not device_identifier:
                continue
            try:
                self._sync_device_security_snapshot(
                    device,
                    active_db=active_db,
                    services=services,
                    dsp_snapshot_cache=dsp_snapshot_cache,
                )
            except Exception as exc:
                logging.warning(
                    "[DSP security poll] Failed to sync device=%s dsp_id=%s: %s",
                    device_identifier,
                    dsp_id,
                    exc,
                    exc_info=True,
                )

    def _run_dsp_threat_poller(self):
        polling_db = self.db_factory() if self.db_factory is not None else self.db
        while not self._poll_stop_event.is_set():
            try:
                self.poll_dsp_threat_updates_once(db_override=polling_db)
            except Exception as exc:
                logging.warning("[DSP threat poll] Iteration failed: %s", exc, exc_info=True)
            self._poll_stop_event.wait(self._poll_interval_seconds)

    def start_dsp_threat_polling(self):
        """Starts backend polling that refreshes DSP snapshots and Threat MUD URLs."""
        if self._poll_thread and self._poll_thread.is_alive():
            return
        self._poll_stop_event.clear()
        self._poll_thread = threading.Thread(
            target=self._run_dsp_threat_poller,
            name="dsp-threat-poller",
            daemon=True,
        )
        self._poll_thread.start()

    def stop_dsp_threat_polling(self):
        """Stops backend polling loop."""
        self._poll_stop_event.set()
    
    def _get_fallback_dsp(self) -> str:
        """
        Returns the hardcoded DSP fallback used in development environments.
        Home Assistant Green IDSP1: no MUD in-instance; MUD is resolved via
        metadata link rel Generic DSP -> genDSP (see MUDService.get_mud_url_from_dsp).
        """
        return get_fallback_idsp_json()

    def _should_use_dsp_fallback(self) -> bool:
        """Enables the hardcoded DSP fallback only when explicitly requested."""
        raw = os.getenv('ALLOW_DSP_FALLBACK', 'false')
        return str(raw).strip().lower() in {'1', 'true', 'yes', 'on'}

    def get_gendsp_from_idsp(
        self,
        idsp_id: str,
        correlation_id: Optional[str] = None,
        device_id: Optional[str] = None,
        feam_service: Optional[FEAMService] = None,
    ) -> str:
        """
        Gets the generic DSP for an Instance DSP ID via FEAM.
        
        Args:
            idsp_id: Instance DSP ID
            
        Returns:
            str: Generic DSP JSON as string (dspFile shape)
        """
        if not idsp_id:
            raise DeviceRegistrationError(
                'IDSP ID is required',
                code='INVALID_REQUEST',
                status_code=400,
                details={'field': 'idsp_id'}
            )

        logging.info("[DSP register] get_gendsp_from_idsp: fetching idsp_id=%s", idsp_id)
        logging.warning("New DSP File retrieved from DSPP. Updating entry in database.")
        active_feam_service = feam_service or self.feam_service
        dsp_json = active_feam_service.fetch_gendsp_payload_from_idsp_id(
            idsp_id,
            version="1.0.0",
            pilot_id=None,
            correlation_id=correlation_id,
            device_id=device_id,
        )
        if dsp_json:
            logging.debug("DSP JSON: %s", dsp_json)
            return dsp_json

        if self._should_use_dsp_fallback():
            dsp_json = self._get_fallback_dsp()
            logging.warning("[DSP register] get_gendsp_from_idsp: using development fallback for idsp_id=%s", idsp_id)
            logging.warning("Using development DSP fallback for IDSP ID %s", idsp_id)
            logging.debug("DSP JSON (fallback): %s", dsp_json)
            return dsp_json

        logging.error(
            "[DSP register] get_gendsp_from_idsp: failed to get GenDSP for idsp_id=%s (no response or status!=ok)",
            idsp_id,
        )
        raise DeviceRegistrationError(
            'Unable to retrieve generic DSP data for the provided IDSP ID',
            code='DSP_FETCH_FAILED',
            status_code=502,
            details={'idsp_id': idsp_id}
        )

    def build_device_from_dsp_payload(self, payload: Dict[str, Any]):
        """
        Builds a Device object from a DSP registration payload.

        Primary fields: idsp_id / idspId.
        Legacy API endpoint still accepts DSP_id / dspId (same POST /api/dsp).
        """
        data = payload or {}
        logging.info("[DSP register] build_device_from_dsp_payload: payload keys=%s", list(data.keys()))
        device_id = str(data.get('device_id') or data.get('deviceId') or '').strip()
        idsp_id = str(
            data.get('idsp_id')
            or data.get('idspId')
            or data.get('DSP_id')
            or data.get('dspId')
            or data.get('dsp_id')
            or ''
        ).strip()
        # No rellenar model con device_id; si no viene, se deja vacío
        model = data.get('model') or None

        if not device_id:
            logging.warning("[DSP register] Validation failed: device_id missing")
            raise DeviceRegistrationError(
                'device_id is required',
                code='INVALID_REQUEST',
                status_code=400,
                details={'field': 'device_id'}
            )

        if not idsp_id:
            logging.warning("[DSP register] Validation failed: idsp_id missing")
            raise DeviceRegistrationError(
                'idsp_id is required',
                code='INVALID_REQUEST',
                status_code=400,
                details={'field': 'idsp_id'}
            )

        logging.info("[DSP register] Parsed: device_id=%s idsp_id=%s model=%s", device_id, idsp_id, model)

        normalized_payload = {
            'device_id': device_id,
            'idsp_id': idsp_id,
            'name': data.get('name'),
            'model': model,
            'type': data.get('type'),
            'manufacturer': data.get('manufacturer'),
            'status': data.get('status', 'active'),
            'ip': data.get('ip'),
            'mac': data.get('mac'),
            'edk': data.get('edk')
        }

        device = self.db.parseDeviceJson(normalized_payload)
        return device

    def register_device_from_dsp_payload(self, payload: Dict[str, Any]):
        """Registers a new device from a DSP payload and returns the created device."""
        logging.info("[DSP register] register_device_from_dsp_payload started")
        device = self.build_device_from_dsp_payload(payload)
        return self.register_dsp_device(device)

    def register_dsp_device(self, device):
        """
        Registers a device with its DSP and returns the created device.

        Raises DeviceRegistrationError on validation or upstream failures.
        """
        logging.info("[DSP register] register_dsp_device: identifier=%s dsp_id=%s",
                     getattr(device, 'identifier', None), getattr(device, 'dsp_id', None))
        if not getattr(device, 'identifier', None):
            raise DeviceRegistrationError(
                'device_id is required',
                code='INVALID_REQUEST',
                status_code=400,
                details={'field': 'device_id'}
            )

        correlation_id = uuid.uuid4().hex

        existing_device = self.db.getDevice(device.identifier)
        if existing_device is not None:
            logging.info("[DSP register] Device already exists: %s", device.identifier)
            logging.info("Device already exists in database.")
            raise DeviceRegistrationError(
                'Device already exists',
                code='DEVICE_ALREADY_EXISTS',
                status_code=409,
                details={'device_id': device.identifier}
            )

        logging.warning(f"New device with identifier {device.identifier} joining. Creating entry in database.")
        logging.info("[DSP register] Fetching GenDSP for idsp_id=%s", device.dsp_id)
        dsp_start = time.perf_counter()
        try:
            dsp = self.get_gendsp_from_idsp(
                device.dsp_id,
                correlation_id=correlation_id,
                device_id=device.identifier,
            )
            device.dsp = dsp
            identity = extract_device_identity_from_gendsp(dsp)
            if identity.get("name"):
                device.name = identity["name"]
            if identity.get("manufacturer"):
                device.manufacturer = identity["manufacturer"]
            if identity.get("model"):
                device.model = identity["model"]
            logging.info(
                "[DSP register] GenDSP identity: name=%s manufacturer=%s model=%s",
                device.name,
                device.manufacturer,
                device.model,
            )
            resolve_pilot_start = time.perf_counter()
            resolved_pilot_id = self.feam_service.resolve_pilot_from_dsp(dsp)
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="resolve_pilot_from_dsp",
                result="completed",
                elapsed_ms=(time.perf_counter() - resolve_pilot_start) * 1000.0,
            )
            if resolved_pilot_id:
                device.pilot_id = resolved_pilot_id
            threat_extract_start = time.perf_counter()
            device.discovered_threat_mud_urls = self._serialize_discovered_threat_urls(
                self.mud_service.get_threat_mud_urls_from_dsp(dsp)
            )
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="extract_threat_mud_urls",
                result="completed",
                elapsed_ms=(time.perf_counter() - threat_extract_start) * 1000.0,
            )
            elapsed_ms = (time.perf_counter() - dsp_start) * 1000.0
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="fetch_dsp",
                result="completed",
                elapsed_ms=elapsed_ms,
            )
        except DeviceRegistrationError as exc:
            elapsed_ms = (time.perf_counter() - dsp_start) * 1000.0
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="fetch_dsp",
                result="failed",
                elapsed_ms=elapsed_ms,
                error_message=exc.message,
            )
            raise
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - dsp_start) * 1000.0
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="fetch_dsp",
                result="failed",
                elapsed_ms=elapsed_ms,
                error_message=str(exc),
            )
            raise DeviceRegistrationError(
                'Unable to retrieve DSP data for the provided DSP ID',
                code='DSP_FETCH_FAILED',
                status_code=502,
                details={'device_id': device.identifier, 'dsp_id': device.dsp_id}
            ) from exc

        logging.info("[DSP register] DSP obtained, resolving MUD for device=%s", device.identifier)

        # Resolve MUD URL
        mudurl_start = time.perf_counter()
        try:
            mudurl = self.mud_service.get_mud_url_from_dsp(device.dsp)
            elapsed_ms = (time.perf_counter() - mudurl_start) * 1000.0
            if not mudurl:
                raise DeviceRegistrationError(
                    'Unable to resolve MUD information from the DSP',
                    code='MUD_RESOLUTION_FAILED',
                    status_code=502,
                    details={'device_id': device.identifier, 'dsp_id': device.dsp_id}
                )
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="resolve_mud_url",
                result="completed",
                elapsed_ms=elapsed_ms,
            )
        except DeviceRegistrationError as exc:
            elapsed_ms = (time.perf_counter() - mudurl_start) * 1000.0
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="resolve_mud_url",
                result="failed",
                elapsed_ms=elapsed_ms,
                error_message=exc.message,
            )
            raise
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - mudurl_start) * 1000.0
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="resolve_mud_url",
                result="failed",
                elapsed_ms=elapsed_ms,
                error_message=str(exc),
            )
            raise DeviceRegistrationError(
                'Unable to resolve MUD information from the DSP',
                code='MUD_RESOLUTION_FAILED',
                status_code=502,
                details={'device_id': device.identifier, 'dsp_id': device.dsp_id}
            ) from exc

        # Fetch MUD file
        mudfile_start = time.perf_counter()
        try:
            ret = self.mud_service.mud_manager_client.get_mud_file(mudurl, device.identifier)
            elapsed_ms = (time.perf_counter() - mudfile_start) * 1000.0
            if ret is None:
                raise DeviceRegistrationError(
                    'Unable to resolve MUD information from the DSP',
                    code='MUD_RESOLUTION_FAILED',
                    status_code=502,
                    details={'device_id': device.identifier, 'dsp_id': device.dsp_id}
                )

            device.mudurl = ret['mudurl']
            device.mudfile = ret['mudfile']
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="resolve_mud",
                result="completed",
                elapsed_ms=elapsed_ms,
            )
        except DeviceRegistrationError as exc:
            elapsed_ms = (time.perf_counter() - mudfile_start) * 1000.0
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="resolve_mud",
                result="failed",
                elapsed_ms=elapsed_ms,
                error_message=exc.message,
            )
            raise
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - mudfile_start) * 1000.0
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="resolve_mud",
                result="failed",
                elapsed_ms=elapsed_ms,
                error_message=str(exc),
            )
            raise DeviceRegistrationError(
                'Unable to resolve MUD information from the DSP',
                code='MUD_RESOLUTION_FAILED',
                status_code=502,
                details={'device_id': device.identifier, 'dsp_id': device.dsp_id}
            ) from exc

        logging.info("[DSP register] MUD resolved. Creating device in DB: %s", device.identifier)

        # Create device in DB
        db_start = time.perf_counter()
        try:
            created = self.db.createdevice(device)
            elapsed_ms = (time.perf_counter() - db_start) * 1000.0
            if not created:
                raise DeviceRegistrationError(
                    'Failed to create device',
                    code='CREATE_FAILED',
                    status_code=500,
                    details={'device_id': device.identifier}
                )
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="create_device_db",
                result="completed",
                elapsed_ms=elapsed_ms,
            )
        except DeviceRegistrationError as exc:
            elapsed_ms = (time.perf_counter() - db_start) * 1000.0
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="create_device_db",
                result="failed",
                elapsed_ms=elapsed_ms,
                error_message=exc.message,
            )
            raise
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - db_start) * 1000.0
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="create_device_db",
                result="failed",
                elapsed_ms=elapsed_ms,
                error_message=str(exc),
            )
            raise DeviceRegistrationError(
                'Failed to create device',
                code='CREATE_FAILED',
                status_code=500,
                details={'device_id': device.identifier}
            ) from exc

        created_device = self.db.getDevice(device.identifier)
        logging.info("[DSP register] Device created successfully: %s", device.identifier)
        logging.info("Device registered successfully.")
        self.db.printDevice(created_device)
        auto_start = time.perf_counter()
        try:
            self._auto_enforce_mud_policies(created_device, correlation_id=correlation_id)
            elapsed_ms = (time.perf_counter() - auto_start) * 1000.0
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="auto_enforce_mud_policies",
                result="completed",
                elapsed_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - auto_start) * 1000.0
            self._record_onboarding_step(
                device_id=device.identifier,
                correlation_id=correlation_id,
                step_name="auto_enforce_mud_policies",
                result="failed",
                elapsed_ms=elapsed_ms,
                error_message=str(exc),
            )
            raise
        self._notify_unapplied_mitigation_gaps_if_any(created_device)
        return created_device

    def _notify_unapplied_mitigation_gaps_if_any(
        self,
        device,
        *,
        db_override=None,
        mitigation_service=None,
    ) -> None:
        """
        When ThreatMUD mitigations exist but enforcement context is incomplete, notify
        eligible users (same path as enforce prerequisites). Dedup prevents repeated sends for the same gaps.
        """
        active_mitigation_service = mitigation_service or self.mitigation_service
        active_db = db_override or self.db
        if active_mitigation_service is None:
            return
        device_id = getattr(device, 'identifier', None)
        if not device_id:
            return
        try:
            mitigations = active_mitigation_service.get_device_mitigations(device_id, device)
        except Exception as exc:
            logging.warning(
                "Proactive mitigation gap notify: get_device_mitigations failed for %s: %s",
                device_id,
                exc,
                exc_info=True,
            )
            return
        n_entries = len(mitigations or [])
        logging.info(
            "Proactive mitigation gap notify: device=%s threat_mitigation_entries=%s",
            device_id,
            n_entries,
        )
        attempted = False
        for entry in mitigations or []:
            if not isinstance(entry, dict):
                continue
            mid = str(entry.get('id') or '')
            if not mid.startswith('threat-mitigation-'):
                continue
            if entry.get('is_enforced'):
                logging.debug(
                    "Proactive mitigation gap notify: skip %s (already enforced / snapshot)", mid
                )
                continue
            eg = entry.get('enforcementGaps') or {}
            if eg.get('ready') is True:
                logging.info(
                    "Proactive mitigation gap notify: skip %s (enforcement context complete; no missing fields)",
                    mid,
                )
                continue
            missing = eg.get('missing') or []
            if not missing:
                logging.info(
                    "Proactive mitigation gap notify: skip %s (ready=false but missing list empty; check gaps warnings: %s)",
                    mid,
                    eg.get('warnings'),
                )
                continue
            threat_id = str(entry.get('threatId') or '')
            threat_data = None
            if threat_id and getattr(active_mitigation_service, 'threat_service', None):
                try:
                    threat_data = active_mitigation_service.threat_service.get_matching_threat_by_id(
                        device, threat_id
                    )
                except Exception as exc:
                    logging.debug(
                        "Proactive mitigation gap notify: get_matching_threat_by_id failed: %s",
                        exc,
                    )
            threat_mud_url = threat_data.get('threat_mud_url') if threat_data else None
            mitigation_name = str(entry.get('name') or f'Threat Mitigation {threat_id}')
            try:
                attempted = True
                logging.info(
                    "Proactive mitigation gap notify: requesting notifications for %s threat=%s missing=%s",
                    mid,
                    threat_id,
                    [m.get('key') if isinstance(m, dict) else m for m in missing],
                )
                NotificationService(active_db).notify_mitigation_prerequisites(
                    device=device,
                    threat_id=threat_id,
                    mitigation_id=mid,
                    threat_mud_url=threat_mud_url,
                    mitigation_name=mitigation_name,
                    missing=list(missing),
                    mspl_index=0,
                )
            except Exception as notify_exc:
                logging.warning(
                    "Proactive mitigation prerequisite notification failed: %s",
                    notify_exc,
                    exc_info=True,
                )
        if n_entries > 0 and not attempted:
            logging.info(
                "Proactive mitigation gap notify: device=%s had %s mitigation row(s) but none with "
                "unread gaps (all enforced, complete context, or no mitigation_actions on matched threats).",
                device_id,
                n_entries,
            )

    def _auto_enforce_mud_policies(
        self,
        device,
        *,
        correlation_id: Optional[str] = None,
        db_override=None,
        policy_service=None,
        policy_enforcement_service=None,
    ):
        """
        Auto-enforces MUD policies when mapped profile is REST and
        profile.auto_enforce_on_registration is enabled.
        """
        active_db = db_override or self.db
        active_policy_service = policy_service or self.policy_service
        active_policy_enforcement_service = policy_enforcement_service or self.policy_enforcement_service
        if active_policy_service is None or active_policy_enforcement_service is None:
            logging.debug("[Auto enforce] Policy services are not configured; skipping.")
            return

        device_id = getattr(device, 'identifier', None)
        if not device_id or not getattr(device, 'mudfile', None):
            return

        try:
            mud_json = json.loads(device.mudfile)
        except Exception as exc:
            logging.warning("[Auto enforce] Cannot parse MUD JSON for device %s: %s", device_id, exc)
            return

        try:
            candidate_policies = active_policy_service.translate_mud_json_to_policies(mud_json, device_id=device_id)
        except Exception as exc:
            logging.error("[Auto enforce] Failed to translate MUD for device %s: %s", device_id, exc, exc_info=True)
            return

        if not candidate_policies:
            return

        persisted = active_db.getPoliciesByDevice(device_id)
        existing_by_hash: Dict[str, Any] = {}
        for policy in persisted:
            source_value = (policy.source or '').strip().lower()
            if source_value not in {'mud', 'mud_file'}:
                continue
            policy_hash = active_policy_service._hash_mspl(policy.mspl_xml)
            current_best = existing_by_hash.get(policy_hash)
            if current_best is None or active_policy_service._policy_rank(policy) > active_policy_service._policy_rank(current_best):
                existing_by_hash[policy_hash] = policy

        for policy_payload in candidate_policies:
            attempt_start = time.perf_counter()
            mspl_xml = policy_payload.get('msplXml')
            if not mspl_xml:
                continue

            mspl_hash = active_policy_service._hash_mspl(mspl_xml)
            policy_name = policy_payload.get('name') or 'MUD Policy'
            policy_type = policy_payload.get('policyType') or 'mud'
            existing_policy = existing_by_hash.get(mspl_hash)

            existing_state_values = {
                str(getattr(existing_policy, 'status', '') or '').strip().lower(),
                str(getattr(existing_policy, 'enforcement_status', '') or '').strip().lower(),
            } if existing_policy is not None else set()

            if existing_policy is not None and getattr(existing_policy, 'enforcement_status', None) == 'completed':
                elapsed_ms = (time.perf_counter() - attempt_start) * 1000.0
                active_policy_enforcement_service.record_execution(
                    device_id=device_id,
                    policy_id=str(existing_policy.id),
                    policy_name=policy_name,
                    profile_id=None,
                    result='skipped',
                    run_mode='execute',
                    is_test=False,
                    event_type="policy_execution",
                    correlation_id=correlation_id,
                    step_name=policy_name,
                    elapsed_ms=elapsed_ms,
                    response_excerpt='skipped (idempotent - already completed)',
                )
                continue

            if existing_policy is not None and 'superseded' in existing_state_values:
                existing_policy.status = 'pending'
                existing_policy.enforcement_status = 'pending'
                existing_policy.enforcement_blockers = None
                active_db.updatePolicy(existing_policy)

            try:
                resolution = active_policy_enforcement_service.resolve_enforcement_profile(mspl_xml)
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - attempt_start) * 1000.0
                active_policy_enforcement_service.record_execution(
                    device_id=device_id,
                    policy_id=str(existing_policy.id) if existing_policy is not None else None,
                    policy_name=policy_name,
                    profile_id=None,
                    result='skipped',
                    run_mode='execute',
                    is_test=False,
                    event_type="policy_execution",
                    correlation_id=correlation_id,
                    step_name=policy_name,
                    elapsed_ms=elapsed_ms,
                    error_message=f'profile resolution failed: {exc}',
                )
                continue

            resolution_mode = str(resolution.get("mode") or "").strip().lower()
            is_sdn_simulated = resolution_mode == "sdn-simulated"

            if not is_sdn_simulated:
                profile_id_raw = resolution.get('profileId')
                if profile_id_raw is None or not str(profile_id_raw).isdigit():
                    elapsed_ms = (time.perf_counter() - attempt_start) * 1000.0
                    active_policy_enforcement_service.record_execution(
                        device_id=device_id,
                        policy_id=str(existing_policy.id) if existing_policy is not None else None,
                        policy_name=policy_name,
                        profile_id=None,
                        result='skipped',
                        run_mode='execute',
                        is_test=False,
                        event_type="policy_execution",
                        correlation_id=correlation_id,
                        step_name=policy_name,
                        elapsed_ms=elapsed_ms,
                        error_message='resolved profile id is invalid',
                    )
                    continue

            profile = None
            profile_id = None
            if not is_sdn_simulated:
                profile_id = int(profile_id_raw)
                profile = active_db.getEnforcementProfile(profile_id)
                if profile is None:
                    elapsed_ms = (time.perf_counter() - attempt_start) * 1000.0
                    active_policy_enforcement_service.record_execution(
                        device_id=device_id,
                        policy_id=str(existing_policy.id) if existing_policy is not None else None,
                        policy_name=policy_name,
                        profile_id=profile_id,
                        result='skipped',
                        run_mode='execute',
                        is_test=False,
                        event_type="policy_execution",
                        correlation_id=correlation_id,
                        step_name=policy_name,
                        elapsed_ms=elapsed_ms,
                        error_message='resolved profile not found',
                    )
                    continue

            if not is_sdn_simulated:
                mode = str(profile.mode or '').strip().lower()
                if not profile.is_active or mode != 'rest' or not bool(getattr(profile, 'auto_enforce_on_registration', False)):
                    elapsed_ms = (time.perf_counter() - attempt_start) * 1000.0
                    active_policy_enforcement_service.record_execution(
                        device_id=device_id,
                        policy_id=str(existing_policy.id) if existing_policy is not None else None,
                        policy_name=policy_name,
                        profile_id=profile.id,
                        result='skipped',
                        run_mode='execute',
                        is_test=False,
                        event_type="policy_execution",
                        correlation_id=correlation_id,
                        step_name=policy_name,
                        elapsed_ms=elapsed_ms,
                        response_excerpt='skipped (profile mode/active/auto-enforce does not match)',
                    )
                    continue

            if existing_policy is not None:
                policy_model = existing_policy
                policy_model.name = policy_name
                policy_model.mspl_xml = mspl_xml
                policy_model.policy_type = policy_type
                policy_model.source = 'mud_file'
                policy_model.status = 'pending'
                policy_model.enforcement_status = 'pending'
                policy_model.enforcement_blockers = None
                active_db.updatePolicy(policy_model)
            else:
                policy_model = active_db.createPolicy(
                    device_id=device_id,
                    name=policy_name,
                    mspl_xml=mspl_xml,
                    policy_type=policy_type,
                    source='mud_file',
                    status='pending',
                    enforcement_status='pending'
                )
                if policy_model is not None:
                    existing_by_hash[mspl_hash] = policy_model

            if not policy_model:
                elapsed_ms = (time.perf_counter() - attempt_start) * 1000.0
                active_policy_enforcement_service.record_execution(
                    device_id=device_id,
                    policy_id=None,
                    policy_name=policy_name,
                    profile_id=profile_id,
                    result='failed',
                    run_mode='execute',
                    is_test=False,
                    event_type="policy_execution",
                    correlation_id=correlation_id,
                    step_name=policy_name,
                    elapsed_ms=elapsed_ms,
                    error_message='failed to create policy row before auto-enforcement',
                )
                continue

            try:
                active_policy_enforcement_service.enforce_policy(
                    mspl_xml,
                    device,
                    policy_name=policy_name,
                    policy_id=str(policy_model.id),
                    run_mode='execute',
                    is_test=False,
                    correlation_id=correlation_id,
                )
                policy_model.status = 'active'
                policy_model.enforcement_status = 'completed'
                policy_model.applied_at = datetime.now(timezone.utc)
                policy_model.enforcement_blockers = None
                active_db.updatePolicy(policy_model)
            except EnforcementPrerequisitesError as exc:
                blockers = json.dumps({"missing": exc.missing}, ensure_ascii=True)
                policy_model.status = 'pending'
                policy_model.enforcement_status = 'deferred'
                policy_model.enforcement_blockers = blockers
                active_db.updatePolicy(policy_model)
                try:
                    NotificationService(active_db).notify_policy_prerequisites(
                        device=device,
                        policy_id=str(policy_model.id),
                        policy_name=policy_name,
                        missing=list(exc.missing or []),
                    )
                except Exception as notify_exc:
                    logging.warning(
                        "[Auto enforce] Prerequisite notification failed: %s",
                        notify_exc,
                        exc_info=True,
                    )
                elapsed_ms = (time.perf_counter() - attempt_start) * 1000.0
                active_policy_enforcement_service.record_execution(
                    device_id=device_id,
                    policy_id=str(policy_model.id),
                    policy_name=policy_name,
                    profile_id=profile_id,
                    result='skipped',
                    run_mode='execute',
                    is_test=False,
                    event_type="policy_execution",
                    correlation_id=correlation_id,
                    step_name=policy_name,
                    elapsed_ms=elapsed_ms,
                    error_message=blockers,
                )
            except Exception as exc:
                logging.error(
                    "[Auto enforce] Enforcement failed for device %s, policy %s: %s",
                    device_id,
                    policy_model.id,
                    exc,
                    exc_info=True
                )
                policy_model.status = 'failed'
                policy_model.enforcement_status = 'failed'
                active_db.updatePolicy(policy_model)
    
    def register_dsp(self, device) -> bool:
        """
        Registers a device with its DSP.
        Equivalent to register_dsp() from the original code (lines 539-561).
        
        Args:
            device: Device object with dsp_id and identifier
            
        Returns:
            bool: True if registered correctly, False if already exists
        """
        try:
            self.register_dsp_device(device)
            return True
        except DeviceRegistrationError as exc:
            logging.warning(f"register_dsp failed for device {getattr(device, 'identifier', None)}: {exc.message}")
            return False
    
    def get_all_devices_dict(self) -> List[Dict]:
        """
        Gets all devices as a list of dictionaries.
        Equivalent to printAllDevices() from the original code.
        
        Returns:
            list: List of dictionaries with device information
        """
        devices = self.db.getAllDevices()
        dvcs = []
        for device in devices:
            dvcs.append(self.db.printDevice(device))
        return dvcs
