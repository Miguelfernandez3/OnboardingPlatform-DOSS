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
- SOFTWARE_REPO_URL (e.g. http://localhost:8081): Url where software repository is listening
- INV_REG_URL (e.g. http://localhost:8080/chain/): Url where inventory and registry is listening
- IDM_URL (e.g. https://localhost:9082/fluidos/idm/): Url where idm is listening for verification requests
- SUUA_URL (e.g. https://suua.api.certify.digital-worx.de/): Url where SUUA API is offered
 

 ## Running the Server

 **IMPORTANTE**: Asegúrate de tener configurado el archivo `.env` antes de ejecutar el servidor.

 To launch the Flask server, which will handle all the routes for registering and querying devices and software, use the following command:

 ```bash
 python app.py
 ```

 Al iniciar, el servidor:
 1. Cargará las variables de entorno desde `.env`
 2. Creará automáticamente el usuario administrador si no existe
 3. Iniciará el servidor Flask en el puerto 4321

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

