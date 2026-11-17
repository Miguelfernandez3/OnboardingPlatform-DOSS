# Onboarding Platform GUI

Interfaz de usuario para la plataforma de onboarding de dispositivos IoT. Permite gestionar dispositivos, visualizar pasaportes digitales, archivos MUD, políticas MSPL y aplicar nuevas políticas de seguridad.

## Arquitectura

Este proyecto sigue una **arquitectura hexagonal (ports & adapters)** que permite:

- **Modularidad**: El API client es completamente modular mediante adapters intercambiables
- **Escalabilidad**: Fácil agregar nuevos adapters para diferentes proyectos
- **Independencia**: No depende de otros proyectos (frontend-bastion, mg_tester)
- **Testabilidad**: Mock API client para desarrollo sin backend

### Estructura del Proyecto

```
src/
├── core/                    # Capa de dominio (hexagonal)
│   ├── domain/             # Entidades y servicios de negocio
│   ├── ports/              # Interfaces/contratos
│   └── adapters/           # Implementaciones (API clients)
├── infrastructure/          # Infraestructura (mock API, schemas)
└── presentation/            # Capa de presentación (React)
    ├── pages/              # Páginas principales
    ├── components/         # Componentes reutilizables
    └── hooks/              # Hooks personalizados
```

## Características

- **Lista de Dispositivos**: Visualización de todos los dispositivos registrados
- **Pasaporte Digital**: Visualización del pasaporte digital del dispositivo (JSON)
- **Archivos MUD**: Consulta y visualización de archivos MUD
- **Políticas MSPL**: 
  - Visualización de políticas aplicadas actualmente
  - Editor visual para crear/editar políticas MSPL
  - Aplicación de políticas directamente o mediante IDSP2 ID
- **Estado de Enforcement**: Monitoreo del estado de aplicación de políticas

## Instalación

```bash
npm install
```

## Desarrollo

```bash
npm run dev
```

La aplicación se ejecutará en `http://localhost:3001`

## Type Checking

```bash
npm run type-check
```

Verifica los tipos TypeScript sin compilar.

## Configuración

### Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# Tipo de adapter a usar: 'doss' o 'json-server'
VITE_API_ADAPTER=json-server

# URL base de la API (solo para adapter 'doss' o 'json-server')
VITE_API_BASE_URL=http://localhost:3000
```

Cuando la GUI se sirve desde Docker (OnboardingPlatform con docker-compose), el contenedor usa nginx para servir los estáticos y hacer proxy de `/api` al domain-manager. En ese caso el build debe usar `VITE_API_BASE_URL=/api` (configurado vía `GUI_VITE_API_BASE_URL=/api` en el compose) para que las peticiones vayan al mismo origen y el proxy funcione.

### Adapters Disponibles

- **json-server**: JSON Server mock API (por defecto en desarrollo)
- **doss**: Adapter para API DOSS

### Mock Server

Para desarrollo sin backend, se incluye un servidor mock independiente basado en JSON Server:

1. **Instalar dependencias del mock-server**:
   ```bash
   cd mock-server
   npm install
   ```

2. **Iniciar el servidor mock**:
   ```bash
   npm start
   ```
   
   El servidor se ejecutará en `http://localhost:3001`

3. **Configurar la aplicación**:
   ```env
   VITE_API_ADAPTER=json-server
   VITE_API_BASE_URL=http://localhost:3001
   ```

El mock-server es un proyecto independiente que puede eliminarse fácilmente cuando ya no sea necesario. Ver `mock-server/README.md` para más detalles.

## Modularidad - Cambiar el API Client

Para usar esta GUI en otro proyecto con diferentes datos/endpoints:

1. **Crear nuevo adapter** en `src/core/adapters/api/[nuevo-proyecto]/`:
   - Crear `[Proyecto]ApiAdapter.js` que extienda `BaseApiClient`
   - Crear `[proyecto].config.js` con la configuración de endpoints

2. **Registrar el adapter** en `src/core/adapters/api/index.js`:
   ```javascript
   case 'nuevo-proyecto':
     return new NuevoProyectoApiAdapter();
   ```

3. **Cambiar variable de entorno**:
   ```env
   VITE_API_ADAPTER=nuevo-proyecto
   ```

4. **La GUI y componentes UI permanecen iguales** - solo cambia el adapter

## Uso

### Listar Dispositivos

Navega a `/devices` para ver todos los dispositivos disponibles.

### Gestionar un Dispositivo

1. Haz clic en "Ver Detalles" en cualquier dispositivo
2. Se abrirá la página de gestión con 4 tabs:
   - **Pasaporte Digital**: Muestra el JSON del pasaporte
   - **Archivo MUD**: Visualiza el archivo MUD del dispositivo
   - **Políticas Aplicadas**: Lista las políticas MSPL actuales
   - **Aplicar Nueva Política**: 
     - Subir IDSP2 ID
     - Crear/editar política MSPL con el editor visual

### Aplicar Política MSPL

1. Ve al tab "Aplicar Nueva Política"
2. Usa el editor visual para construir la política MSPL
3. El XML se genera automáticamente en tiempo real
4. Haz clic en "Aplicar Política" para enviarla al dispositivo

### Aplicar IDSP2

1. Ve al tab "Aplicar Nueva Política"
2. Ingresa el IDSP2 ID en el campo correspondiente
3. Haz clic en "Aplicar IDSP2"

## API Endpoints (Placeholders)

Los siguientes endpoints están definidos como placeholders y deben ser implementados en el backend:

- `GET /api/devices` - Lista dispositivos
- `GET /api/devices/:id` - Detalles dispositivo
- `GET /api/devices/:id/passport` - Pasaporte digital
- `GET /api/devices/:id/mud` - Archivo MUD
- `GET /api/devices/:id/policies` - Políticas aplicadas
- `POST /api/devices/:id/apply-idsp2` - Aplicar IDSP2 ID
- `POST /api/devices/:id/apply-policy` - Aplicar política MSPL
- `GET /api/devices/:id/enforcement-status` - Estado de enforcement

## Tecnologías

- **TypeScript**: Lenguaje de programación con tipado estático
- **React 18**: Framework UI
- **React Router**: Navegación
- **Vite**: Build tool
- **react-ace**: Editor XML
- **xmlbuilder2**: Generación XML
- **react-syntax-highlighter**: Syntax highlighting
- **i18next & react-i18next**: Internacionalización (i18n) - Soporte para español e inglés

## Estructura de Componentes

### Componentes MSPL

- `PolicyBuilder`: Constructor visual de políticas MSPL
- `XmlViewer`: Visualizador de XML con syntax highlighting
- `MSPLEditor`: Combina PolicyBuilder + XmlViewer
- `MSPLViewer`: Visualizador simple de XML MSPL

### Componentes de Políticas

- `PolicyList`: Lista políticas aplicadas
- `IDSP2Uploader`: Componente para aplicar IDSP2 ID
- `EnforcementStatus`: Muestra estado de enforcement

### Componentes Comunes

- `JsonViewer`: Visualizador JSON genérico
- `LoadingSpinner`: Spinner de carga
- `MUDViewer`: Visualizador de archivos MUD

## Flujo de Datos

```
UI Components → Hooks → API Client (Adapter) → Backend API
                ↓
         Domain Services
                ↓
         Domain Entities
```

Los componentes UI usan hooks que consumen el API client a través de la interfaz `IApiClient`. El adapter concreto (DossApiAdapter, JsonServerApiClient, etc.) se inyecta mediante el factory en `config.ts`.

## Desarrollo sin Backend

Por defecto, la aplicación usa el `JsonServerApiClient` que consume la API REST del mock-server (JSON Server). Esto permite desarrollar y probar la GUI con un servidor HTTP real sin necesidad del backend completo.

**Para usar el mock-server:**

1. Inicia el mock-server (ver sección "Mock Server" arriba)
2. La aplicación se conectará automáticamente si `VITE_API_ADAPTER=json-server` (valor por defecto)

**Para cambiar al adapter DOSS:**

```env
VITE_API_ADAPTER=doss
VITE_API_BASE_URL=http://localhost:3000/api
```

## Internacionalización (i18n)

La aplicación soporta múltiples idiomas mediante i18next. Actualmente disponible:

- **Inglés (en)**: Idioma por defecto
- **Español (es)**

### Cambiar Idioma

El selector de idioma está disponible en la barra de navegación. El idioma seleccionado se guarda en `localStorage` y se mantiene entre sesiones.

### Agregar Nuevos Idiomas

1. Crear archivo de traducción en `src/i18n/locales/[codigo-idioma].json`
2. Agregar el recurso en `src/i18n/config.ts`
3. Agregar botón en `LanguageSelector.tsx` si se desea

### Estructura de Traducciones

Las traducciones están organizadas por secciones:
- `common`: Textos comunes (botones, estados, etc.)
- `navbar`: Navegación
- `devices`: Lista de dispositivos
- `device`: Gestión de dispositivo individual
- `policies`: Políticas MSPL
- `enforcement`: Estado de enforcement
- `policyBuilder`: Editor de políticas
- `xmlViewer`: Visualizador XML
- `jsonViewer`: Visualizador JSON

