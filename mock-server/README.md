# Mock Server - JSON Server

Servidor mock independiente para desarrollo de la aplicación onboarding-platform-gui.

## Instalación

```bash
npm install
```

## Uso

Inicializar la base de datos (si no existe `db.json`):

```bash
npm run init-db
```

Iniciar el servidor:

```bash
npm start
```

El servidor se ejecutará en `http://localhost:3000`

**Nota**: Si `db.json` no existe, se inicializará automáticamente desde `db_example.json` al ejecutar `npm start` o `npm run dev`.

## Estructura de Datos

El archivo `db.json` contiene las siguientes colecciones:

- **devices**: Dispositivos IoT registrados
- **policies**: Políticas MSPL aplicadas a dispositivos
- **threats**: Amenazas asociadas a dispositivos
- **mitigations**: Mitigaciones para amenazas
- **passports**: Pasaportes digitales de dispositivos
- **muds**: Archivos MUD de dispositivos
- **enforcementStatuses**: Estados de enforcement de políticas

## Endpoints Disponibles

JSON Server expone automáticamente los siguientes endpoints REST:

- `GET /devices` - Lista todos los dispositivos
- `GET /devices/:id` - Obtiene un dispositivo específico
- `GET /policies?deviceId=:id` - Obtiene políticas de un dispositivo
- `GET /threats?deviceId=:id` - Obtiene threats de un dispositivo
- `GET /mitigations?deviceId=:id` - Obtiene mitigations de un dispositivo
- `GET /passports?deviceId=:id` - Obtiene passport de un dispositivo
- `GET /muds?deviceId=:id` - Obtiene MUD de un dispositivo
- `GET /enforcementStatuses?deviceId=:id` - Obtiene estado de enforcement

También soporta:
- `POST /devices` - Crear dispositivo
- `PUT /devices/:id` - Actualizar dispositivo
- `PATCH /devices/:id` - Actualizar parcialmente dispositivo
- `DELETE /devices/:id` - Eliminar dispositivo

(Similar para otras colecciones)

## Rutas Personalizadas

El archivo `routes.json` define rutas personalizadas para relaciones REST:

- `/devices/:id/policies` → `/policies?deviceId=:id`
- `/devices/:id/threats` → `/threats?deviceId=:id`
- `/devices/:id/mitigations` → `/mitigations?deviceId=:id`
- `/devices/:id/passport` → `/passports?deviceId=:id`
- `/devices/:id/mud` → `/muds?deviceId=:id`
- `/devices/:id/enforcement-status` → `/enforcementStatuses?deviceId=:id`

## Resetear Datos

Para resetear los datos a su estado inicial:

```bash
# Opción 1: Copiar manualmente desde el ejemplo
cp db_example.json db.json

# Opción 2: Eliminar db.json y reiniciar el servidor (se inicializará automáticamente)
rm db.json && npm start
```

O simplemente edita `db.json` manualmente y el servidor se recargará automáticamente.

## Notas

- Los cambios se guardan automáticamente en `db.json`
- El servidor se recarga automáticamente cuando cambias `db.json`
- Este servidor es solo para desarrollo y testing
- No usar en producción
