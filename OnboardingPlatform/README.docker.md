# OnboardingPlatform con Docker Compose

Este setup levanta toda la plataforma con un único comando:

- `Domain-Manager` (API principal)
- `Extended-MUD-Manager` (MUD)
- `Extended-MUD-Manager` (Threat MUD)
- `Extended-MUD-Server`
- `onboarding_platform_gui`

`Policy_Translator` y `shared_auth` no se levantan como servicios separados porque son librerías internas que ya se empaquetan dentro de las imágenes que las usan.

## 1) Preparar variables

Desde `doss/OnboardingPlatform`:

```bash
cp .env.compose.example .env.compose
```

**No hace falta crear un `.env` aparte**: las variables se cargan desde `.env.compose` (los servicios usan `env_file: .env.compose`). Para que la sustitución en el `docker-compose.yml` también use ese fichero, levanta con `--env-file .env.compose` (ver apartado 2).

Edita al menos:

- `JWT_SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `DADM_DATABASE_PATH` si quieres mover la SQLite a otra ruta dentro del contenedor

Recomendado para enforcement Home Assistant:

- `HOME_ASSISTANT_TOKEN`

Si tus DSPs incluyen MUD URLs con `localhost` (por ejemplo `http://localhost:8091/...`), mantén:

- `LOCALHOST_ALIAS_BY_PORT=8091:mud-server,8888:mud-manager,8889:threat-mud-manager,4321:domain-manager,3001:gui`

Fallbacks opcionales:

- `MUD_LOCALHOST_ALIAS=mud-server`
- `THREAT_MUD_LOCALHOST_ALIAS=mud-server`

## 2) Levantar todo

```bash
docker compose --env-file .env.compose up --build
```

Si tu instalación usa la sintaxis clásica:

```bash
docker-compose --env-file .env.compose up --build
```

## 3) Endpoints

- GUI: `http://localhost:3001`
- Domain-Manager API: `http://localhost:4321`
- MUD Manager: `http://localhost:8888`
- Threat MUD Manager: `http://localhost:8889`
- MUD Server: `http://localhost:8091`

## Persistencia de datos

- El `domain-manager` persiste su SQLite en el volumen Docker `domain-manager-data`.
- La ruta por defecto dentro del contenedor es `/var/lib/onboardingplatform/domain-manager/DeviceDomainManager.db`.
- Si necesitas reinicializar completamente la base de datos, para los servicios y elimina el volumen:

```bash
docker compose --env-file .env.compose down -v
```

Después vuelve a levantar:

```bash
docker compose --env-file .env.compose up --build
```

## 4) Parar servicios

```bash
docker compose --env-file .env.compose down
```

o:

```bash
docker-compose --env-file .env.compose down
```
