/**
 * Token storage for JWT auth (SimpleJWT on the backend: /api/auth/signup/,
 * /api/auth/login/, /api/auth/logout/, /api/auth/refresh/).
 */

const ACCESS_TOKEN_KEY = "recon_dashboard_access_token";
const REFRESH_TOKEN_KEY = "recon_dashboard_refresh_token";
export const AUTH_CHANGED_EVENT = "auth-changed";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, access);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
   window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export function clearTokens(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
   window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}
