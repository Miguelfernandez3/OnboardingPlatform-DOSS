/**
 * Token Storage - Utilidad para gestión de tokens JWT
 * Almacena y recupera tokens de acceso y refresh desde localStorage
 */

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

/**
 * Obtiene el token de acceso del localStorage
 */
export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

/**
 * Obtiene el token de refresh del localStorage
 */
export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

/**
 * Guarda los tokens en localStorage
 */
export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

/**
 * Limpia los tokens del localStorage
 */
export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

/**
 * Verifica si un token JWT está expirado
 * Decodifica el payload del JWT y verifica el campo 'exp'
 */
export function isTokenExpired(token: string): boolean {
  try {
    // Decodificar el payload del JWT (sin verificar la firma)
    const parts = token.split('.');
    if (parts.length !== 3) {
      return true; // Token inválido, considerar expirado
    }

    const payload = JSON.parse(atob(parts[1]));
    const exp = payload.exp;

    if (!exp) {
      return true; // No tiene expiración, considerar expirado
    }

    // exp está en segundos, Date.now() está en milisegundos
    const expirationTime = exp * 1000;
    const currentTime = Date.now();

    return currentTime >= expirationTime;
  } catch (error) {
    // Si hay error al decodificar, considerar expirado
    return true;
  }
}

/**
 * Obtiene el tiempo de expiración del token en milisegundos
 */
export function getTokenExpirationTime(token: string): number | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) {
      return null;
    }

    const payload = JSON.parse(atob(parts[1]));
    const exp = payload.exp;

    if (!exp) {
      return null;
    }

    return exp * 1000; // Convertir a milisegundos
  } catch (error) {
    return null;
  }
}
