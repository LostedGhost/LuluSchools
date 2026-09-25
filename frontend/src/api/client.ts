import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import type { ApiErrorBody, TokenPair } from "../types/api";

const ACCESS_TOKEN_KEY = "lulu_access_token";
const REFRESH_TOKEN_KEY = "lulu_refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function storeTokens(tokens: TokenPair): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export const api = axios.create({
  baseURL: "/api/v1",
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

interface RequeteAvecRetry extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

let refreshEnCours: Promise<string | null> | null = null;

async function rafraichirToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  try {
    const { data } = await axios.post<TokenPair>("/api/v1/auth/refresh", {
      refresh_token: refreshToken,
    });
    storeTokens(data);
    return data.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const requeteOriginale = error.config as RequeteAvecRetry | undefined;
    if (error.response?.status === 401 && requeteOriginale && !requeteOriginale._retry) {
      requeteOriginale._retry = true;
      if (!refreshEnCours) {
        refreshEnCours = rafraichirToken().finally(() => {
          refreshEnCours = null;
        });
      }
      const nouveauToken = await refreshEnCours;
      if (nouveauToken) {
        requeteOriginale.headers = requeteOriginale.headers ?? {};
        requeteOriginale.headers.Authorization = `Bearer ${nouveauToken}`;
        return api.request(requeteOriginale);
      }
      window.location.href = "/connexion";
    }
    return Promise.reject(error);
  },
);

export function messageErreur(error: unknown, defaut = "Une erreur est survenue."): string {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as ApiErrorBody | undefined;
    if (body?.error?.message) return body.error.message;
  }
  return defaut;
}

export function codeErreur(error: unknown): string | null {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as ApiErrorBody | undefined;
    return body?.error?.code ?? null;
  }
  return null;
}
