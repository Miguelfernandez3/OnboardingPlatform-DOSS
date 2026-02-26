/// <reference types="vite/client" />

/**
 * Declaración de tipos para variables de entorno de Vite
 * Las variables de entorno deben tener el prefijo VITE_ para ser expuestas
 */
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_ADAPTER?: string;
}

