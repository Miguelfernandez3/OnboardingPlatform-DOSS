"""
Hardcoded Home Assistant Green IDSP1 fallback for development.
No MUD in-instance; MUD resolved via metadata link rel Generic DSP -> genDSP.
Used when ALLOW_DSP_FALLBACK is set (DeviceService) and legacy getDSP fallback (DeviceDomainManager).
"""
import json
from typing import Any, Dict

FALLBACK_IDSP: Dict[str, Any] = {
    "doss-dsp": {
        "uuid": "bbae8107-3deb-599c-909a-bb60ab37aae1",
        "metadata": {
            "title": "Home Assistant Green IDSP1",
            "published": "2025-12-10T12:00:00Z",
            "last-modified": "2025-12-10T12:00:00Z",
            "version": "1.0.0",
            "dsp-model-version": "1.0.0",
            "revisions": [
                {
                    "title": "Initial Release",
                    "published": "2025-12-10",
                    "description": "Initial version of the DSP document.",
                    "version": "1.0.0",
                    "dsp-model-version": "1.0.0",
                    "modified-by": {
                        "role-id": "system-owner",
                        "party-uuid": "f02bc8f7-21a5-50f2-a400-7a3c117c521a",
                    },
                }
            ],
            "links": [
                {
                    "href": "https://drive.google.com/uc?export=download&id=1wCFc2q7-Gpd0VvbQyBKhwLzVFP3DSsGw",
                    "rel": "Generic DSP",
                    "text": "bbae8107-3deb-599c-909a-bb60ab37aae1",
                }
            ],
            "roles": [
                {
                    "id": "system-owner",
                    "title": "System Owner",
                    "description": "Responsible for device management in operational context",
                },
                {
                    "id": "manufacturer",
                    "title": "Manufacturer",
                    "description": "Creator of the device",
                },
            ],
            "parties": [
                {
                    "uuid": "d26858b4-7b49-57dc-815a-ab289039c4d8",
                    "type": "organization",
                    "name": "Nabu Casa",
                    "remarks": "Manufacturer and official vendor of Home Assistant Green",
                },
                {
                    "uuid": "f02bc8f7-21a5-50f2-a400-7a3c117c521a",
                    "type": "organization",
                    "name": "CERTH",
                    "remarks": "Owner of the Home Assistant Green smart home controller",
                },
            ],
            "responsible-parties": [
                {
                    "role-id": "system-owner",
                    "party-uuid": "f02bc8f7-21a5-50f2-a400-7a3c117c521a",
                }
            ],
        },
        "system-id": {
            "identifier-type": "urn:fdo:device-id",
            "id": "EDBA506B90E1420298485E91160CB16F",
        },
        "local-definitions": {
            "components": [
                {
                    "uuid": "a7af2b1d-3d15-5e81-97af-f4142f75f4ad",
                    "type": "this-system",
                    "title": "Home Assistant Green",
                    "description": "Home Assistant Green Smart Home Hub.",
                    "purpose": "Core smart home controller and integration platform.",
                    "props": [
                        {"name": "vendor", "value": "Nabu Casa"},
                        {"name": "model", "value": "Home Assistant Green"},
                        {"name": "version", "value": "1.0.0"},
                    ],
                    "links": [
                        {
                            "href": "https://drive.google.com/uc?export=download&id=1eyDty6TAi5UBuE__QZZJqttg-VaHBP2K",
                            "rel": "CBOM file",
                            "media-type": "application/vnd.cyclonedx+json",
                        }
                    ],
                    "status": {"state": "operational"},
                },
                {
                    "uuid": "77af2b1d-dd15-8881-ffaf-f41425671333",
                    "type": "service",
                    "title": "FDO device onboard",
                    "description": "Secure device onboarding using FDO",
                    "purpose": "Device Onboarding",
                    "props": [
                        {"name": "vendor", "value": "UMU"},
                        {"name": "model", "value": "FDO_onboard"},
                        {"name": "version", "value": "1.0.0"},
                    ],
                    "links": [
                        {
                            "href": "https://vault.company.com/fdo/vouchers/EDBA506B90E1420298485E91160CB16F",
                            "rel": "ownership-voucher",
                            "media-type": "application/cbor",
                        }
                    ],
                    "status": {"state": "operational"},
                },
            ]
        },
    }
}


def get_fallback_idsp_json() -> str:
    """Serialized IDSP fallback for storage and MUDService chain resolution."""
    return json.dumps(FALLBACK_IDSP)
