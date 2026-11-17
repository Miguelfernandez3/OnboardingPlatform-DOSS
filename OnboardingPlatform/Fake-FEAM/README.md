# Fake-FEAM

HTTP stub that implements the same endpoints the Domain-Manager [FEAMClient](../Domain-Manager/clients/feam_client.py) uses:

- `POST /checkPin`
- `POST /getFunctionsOwn` (returns [catalog.json](catalog.json) — same operation IDs as [test_feam_service.DummyFEAMClient](../Domain-Manager/tests/test_feam_service.py))
- `POST /callResourceServer` (serves Instance-DSP and GenDSP documents from files on disk)

## Layout

- `files/gendsp/<uuid>.json` — each file is a **dspFile** object: `{"doss-dsp": { "uuid": "…", ... }}`
- `files/insdsp/<uuid>.json` — same
- The file name (without `.json`) must match `doss-dsp.uuid` (lowercase) so list-by-id and lookups stay consistent

## Run locally

```bash
cd OnboardingPlatform/Fake-FEAM
pip install -r requirements.txt
# default port 8181; override with PORT=8190
python app.py
```

## Point Domain-Manager to Fake-FEAM (IP or Docker DNS)

The Domain-Manager reads the FEAM base URL from `FEAM_SERVER_URL` or `FEAM_SERVER` (see [config.py](../Domain-Manager/core/config.py)) — same pattern as `MUD_MANAGER_URL`.

**Examples**

- Local: `export FEAM_SERVER_URL=http://127.0.0.1:8181`
- Docker Compose service name: `FEAM_SERVER_URL=http://fake-feam:8181` (if `fake-feam` is on the same network)
- From a container to the host (see [docker-compose.yml](../docker-compose.yml)): `FEAM_SERVER_URL=http://host.docker.internal:8181`

Optional:

- `FAKEFEAM_FILES_DIR` — override directory for `gendsp` / `insdsp` (default: this folder’s `files/`)
- `FAKEFEAM_CATALOG_PATH` — override [catalog.json](catalog.json) path
- `PORT` / `FAKEFEAM_LISTEN` — listen port (default 8181)

## OperationId suffixes (must match [feam_service.py](../Domain-Manager/services/feam_service.py))

| Suffix | Behaviour |
|--------|------------|
| `0539-4440-be7d-ba743f8c4ada` | list GenDSP (all `files/gendsp/*.json`) |
| `cc5b-44e9-adce-159aee6c0c6d` | list InsDSP |
| `b492-4267-9ef5-92b15f22a394` | get InsDSP by `extraValues[0]` → `{"id":"<uuid>",...}` |
| `4637-487c-a71a-9cba257304af` | get GenDSP by id |
| `ad05-4b4f-a4df-6551238ca72b` | list reports → `[]` (for FEAM sync) |

## Sample DSP IDs (from [../actual_dsp.json](../actual_dsp.json), GenDSP)

All four documents in that file are exported as `files/gendsp/<doss-dsp-uuid>.json`:

| `dsp_id` (GenDSP) | File |
|-------------------|------|
| `bbae8107-3deb-599c-909a-bb60ab37aae1` | Home Assistant Green |
| `6c5111a4-ac1f-5605-8636-67040e99d62e` | Athom LB01-15W E27 Smart Bulb |
| `11545605-046f-5715-a842-f500bb065bf7` | RuuviTag Smart Thermometer |
| `4616a400-1fe2-5501-8c9d-49a6daabdd05` | SONOFF TH16 Smart Thermostat |

Each GenDSP links to local MUD/ThreatMUD files on `http://doss-mud-registry.eu/<name>` (served by Extended-MUD-Server). Names follow the four HA mitigations defined by Ilias (smart home lab):

| Registry base name | Ilias mitigation |
|--------------------|------------------|
| `home-assistant-mud` / `home-assistant-threatmud` | Block all DOSS devices on Home Assistant |
| `smart-lamp-mud` / `smart-lamp-threatmud` | Block access to smart lamp |
| `thermometer-mud` / `thermometer-threatmud` | Block access to thermometer |
| `thermostat-mud` / `thermostat-threatmud` | Block access to thermostat |

ThreatMUD MSPL entries reference ObP enforcement profiles wired to Ilias endpoints (`ha-block-all-doss-devices`, `ha-block-smart-lamp`, `ha-turn-off-thermometer`, `ha-turn-off-thermostat`).

## Home Assistant enforcement context

Child devices (lamp, thermometer, thermostat) invoke mitigation REST calls against the **Home Assistant hub IP** (e.g. `160.40.54.46`), not their own IP. After registering a device, set `enforcement_context.ha_ip`:

```bash
curl -X PUT http://localhost:4321/api/devices/<device_id> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"enforcement_context": {"ha_ip": "160.40.54.46"}}'
```

ObP matches threats primarily via the `threat mud` link URL discovered from each device's DSP at registration (not via invented model slugs).

Seed enforcement secrets and profiles (requires `HA_MAIN_BEARER` and `HA_LAMP_BEARER` env vars):

```bash
cd Domain-Manager
python3 scripts/seed_ha_enforcement.py
```

See [Extended-MUD-Server/files/](../Extended-MUD-Server/files/) for `home-assistant-*`, `smart-lamp-*`, `thermometer-*`, and `thermostat-*` MUD/ThreatMUD JSON files.

- InsDSP example (synthetic, not in `actual_dsp.json`): `11111111-1111-1111-1111-111111111111` ([files/insdsp/11111111-1111-1111-1111-111111111111.json](files/insdsp/11111111-1111-1111-1111-111111111111.json))

## Docker

Build from the `OnboardingPlatform` context (as other services in this repo):

```bash
docker build -f Fake-FEAM/Dockerfile .
docker run -p 8181:8181 <image>
```

`docker compose` in [docker-compose.yml](../docker-compose.yml) includes a `fake-feam` service on port 8181; the default for `domain-manager` is `FEAM_SERVER_URL=http://fake-feam:8181`. For FEAM on the **host** instead, set `FEAM_SERVER_URL=http://host.docker.internal:8181` and run Fake-FEAM locally, or port-forward.

## FEAM sync polling

To reduce noise if you do not need real pilot sync, increase or disable the Domain-Manager poll interval, e.g. `FEAM_SYNC_POLL_INTERVAL_SECONDS=0` (see [config.py](../Domain-Manager/core/config.py)).
