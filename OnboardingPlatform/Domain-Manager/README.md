 # Device and Domain Manager 

 ## Setting Up Environment
The requirements.txt file contains the dependencies necessary for running the code. You can install (in a python venv if needed) them through 
```
pip install -r requirements.txt
```

 ## Configuration

### Variables de Entorno Requeridas para Autenticación
Crea manualmente el archivo `.env` con las siguientes variables:

```env
# JWT Secret Key - REQUERIDO (mínimo 32 caracteres)
JWT_SECRET_KEY=tu_secret_key_super_seguro_aqui

# Credenciales del Administrador Inicial - REQUERIDO
ADMIN_EMAIL=email_del_usuario_administrador_aqui
ADMIN_PASSWORD=tu_password_seguro_aqui
```

**Variables Requeridas:**
- `JWT_SECRET_KEY`: Clave secreta para firmar tokens JWT (generar con: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `ADMIN_EMAIL`: Email del usuario administrador inicial
- `ADMIN_PASSWORD`: Password del administrador (mínimo 8 caracteres)

El usuario administrador se creará automáticamente al iniciar la aplicación si no existe.

### Otras Variables de Entorno (Opcionales)
- LOG_LEVEL (e.g. DEBUG): Define level of logging
- LOG_OUTPUT (e.g. STDOUT): Define output stream for logging. STDOUT or STDERR, otherwise will be treated as a filename. 
- DADM_PORT (e.g. 4321): Port where the server will listen
- DADM_DATABASE_PATH (e.g. `DeviceDomainManager.db` or `/var/lib/onboardingplatform/domain-manager/DeviceDomainManager.db`): SQLite file path used by Domain-Manager
- DADM_DATABASE_URL (advanced): Full SQLAlchemy database URL. If defined, it takes precedence over `DADM_DATABASE_PATH`
- SOFTWARE_REPO_URL (e.g. http://localhost:8081): Url where software repository is listening
- INV_REG_URL (e.g. http://localhost:8080/chain/): Url where inventory and registry is listening
- IDM_URL (e.g. https://localhost:9082/fluidos/idm/): Url where idm is listening for verification requests
- SUUA_URL (e.g. https://suua.api.certify.digital-worx.de/): Url where SUUA API is offered
- ENFORCEMENT_ALLOWED_HOSTS: Lista separada por comas de hosts permitidos para `endpoint_template` (ej. `localhost,127.0.0.1,.example.org`). Usar `*` para permitir cualquier dominio (sin comprobación de host).
- ENFORCEMENT_KEYS_JSON: JSON con material de claves AES-GCM versionadas (ej. `{"v1":"<base64-32bytes>"}`)
- ENFORCEMENT_ACTIVE_KEY_VERSION: Versión activa para cifrado de secretos (ej. `v1`)

### Enforcement (solo base de datos)
- La configuración de enforcement ya no se lee desde `config.yaml` en runtime.
- Perfiles, mappings y secretos se gestionan exclusivamente por APIs admin o CLI.
- Si no hay configuración activa en BD, la app arranca igualmente pero:
  - `POST /api/devices/<device_id>/policies/<policy_id>/enforce` devuelve `503` con `ENFORCEMENT_NOT_CONFIGURED`.
  - El auto-enforcement en registro de dispositivos se registra como `skipped`.
 

 ## Running the Server

 **IMPORTANTE**: Asegúrate de tener configurado el archivo `.env` antes de ejecutar el servidor.

 To launch the Flask server, which will handle all the routes for registering and querying devices and software, use the following command:

 ```bash
 python app.py
 ```

 Al iniciar, el servidor:
1. Cargará las variables de entorno desde `.env`
2. Resolverá la ruta de base de datos y creará el directorio si hace falta
3. Aplicará migraciones SQLite no destructivas para columnas nuevas en bases existentes
4. Creará automáticamente el usuario administrador si no existe
5. Iniciará el servidor Flask en el puerto configurado

### Autenticación

Todos los endpoints (excepto `/api/auth/login`) requieren autenticación JWT.

**IMPORTANTE**: Los usuarios no pueden registrarse por sí mismos. Solo los administradores pueden crear usuarios a través del endpoint `POST /api/users` (requiere autenticación de admin).

Para autenticarte:
1. Inicia sesión con credenciales proporcionadas por un administrador: `POST /api/auth/login` (retorna `access_token` y `refresh_token`)
2. Usa el token en las peticiones: `Authorization: Bearer <access_token>`

**Gestión de usuarios (solo administradores):**
- `GET /api/users` - Listar usuarios con paginación
- `POST /api/users` - Crear nuevo usuario
- `GET /api/users/<user_id>` - Obtener usuario
- `PUT /api/users/<user_id>/role` - Cambiar rol de usuario
- `DELETE /api/users/<user_id>` - Eliminar usuario (soft delete)
- `POST /api/users/<user_id>/activate` - Reactivar usuario

Para más información sobre la API de autenticación, consulta los endpoints en `api/auth.py` y `api/users.py`.

## API Calls
The API calls cover functionality described in the flows (such as software upgrade demo) as REST APIs.

### Policy enforcement endpoint
- `POST /api/devices/<device_id>/policies/<policy_id>/enforce`
  - Enforces an existing policy using configured type->enforcement mappings.
  - For MUD-derived policies, use IDs returned by `GET /api/devices/<device_id>/policies` (e.g., `mud-policy-0`).
  - If no active DB configuration is available, returns `503` with code `ENFORCEMENT_NOT_CONFIGURED`.
- `POST /api/policies/translate-mud`
  - Receives a full MUD JSON and returns translated policies in MSPL format plus enforcement metadata preview.

### Resolución de contexto y estado `deferred` (enforcement)

- **Orden de fusión del contexto** (el último valor gana en caso de clave duplicada): carga `base` del flujo, MSPL/derivado del mapeo, `device.enforcement_context` (JSON, sustituido con `PUT /api/devices/<device_id>`), y en `POST /api/devices/<device_id>/policies/<policy_id>/enforce` el cuerpo opcional `extraContext` (misma petición, sin persistirlo).
- **`context_spec` en perfiles** (`/api/admin/enforcement/profiles`): declara claves requeridas o el modo con placeholders; si faltan datos, el preflight de enforcement falla con `409` y cuerpo `missing`, y el auto-enforcement deja la política en `deferred` y guarda pistas en `enforcement_blockers` (en la entidad de política).
- **Comprobar huecos sin ejecutar**: `GET /api/devices/<device_id>/policies/<policy_id>/enforcement-gaps` (lista faltante respecto al perfil / contexto resuelto).
- **Bases de datos no SQLite** (p. ej. PostgreSQL con esquema ya creado): al migrar manualmente, añadir columnas análogas, por ejemplo:
  - `policy` / tabla equivalente: `enforcement_blockers` (texto/JSON) si aplica al modelo; `enforcement_status` con valor `deferred` permitido;
  - `device`: `enforcement_context` (texto/JSON);
  - `enforcement_profile` (o `policy`): `context_spec` (texto/JSON) según el modelo. Consulta `Database.py` y `SQLITE_COLUMN_MIGRATIONS` para los nombres exactos.

### Admin enforcement endpoints (`require_admin`)
- `GET|POST /api/admin/enforcement/profiles`
- `GET|PUT|DELETE /api/admin/enforcement/profiles/<id>`
- `GET|POST /api/admin/enforcement/mappings`
- `GET|PUT|DELETE /api/admin/enforcement/mappings/<id>`
- `GET|POST /api/admin/enforcement/secrets`
- `GET|PUT|DELETE /api/admin/enforcement/secrets/<id>` (el valor secreto nunca se devuelve)
- `POST /api/admin/enforcement/test` (`runMode=preview|execute`)
- `GET /api/admin/enforcement/executions` (filtros: `from`, `to`, `result`, `deviceId`, `isTest`, `profileId`, `limit`)


 ### Error Handling
 - **200 OK**: Success, with a field including data as needed.
 - **400 Bad Request**: Invalid inputs or missing fields.
 - **401/403 Unauthorized**: Invalid or missing credentials.
 - **500 Internal Server Error**: Errors related to server or backend logic.



 ### Testing API calls
 You can get a summary of the available API calls through:
 ```bash
 curl -X GET http://localhost:$DADM_PORT/ 
 ```


 To register a device:

 ```bash
 curl -X POST http://localhost:$DADM_PORT/register_device \
 -H "Content-Type: application/json" \
 -d '{
     "mac": "00:1B:44:11:3A:B7",
     "firmware_version": "1.0.0",
     "name": "Test Device",
     "device_id": "12345", 
     "v_cred": {
         "type": "Credentials",
         "data": "Valid"
     }
 }'
 ```

To register software:

 ```bash
 curl -X POST http://localhost:$DADM_PORT/register_software \
 -H "Content-Type: application/json" \
 -d '{
     "sw_identifier": "SW100",
     "sw_version": "v1.0",
     "name": "Software Name"
 }'
 ```

 To update status:

 ```bash
 curl -X POST http://localhost:$DADM_PORT/update_status \
 -H "Content-Type: application/json" \
 -d '{
     "device_id": "12345", // Mandatory for inventory updates
     "update_id": "update123",
     "status": "success"
 }'
 ```
