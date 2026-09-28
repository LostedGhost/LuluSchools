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

export async function rafraichirToken(): Promise<string | null> {
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

/** Un seul rafraichissement a la fois, partage entre axios et les appels fetch (flux SSE). */
export function rafraichirUneFois(): Promise<string | null> {
  if (!refreshEnCours) {
    refreshEnCours = rafraichirToken().finally(() => {
      refreshEnCours = null;
    });
  }
  return refreshEnCours;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    // Téléchargement (responseType "blob") : le corps d'erreur JSON arrive en Blob ; on le
    // relit pour que messageErreur/codeErreur affichent le vrai message du serveur.
    if (error.response?.data instanceof Blob && error.response.data.type.includes("json")) {
      try {
        error.response.data = JSON.parse(await error.response.data.text());
      } catch {
        /* corps illisible : message générique */
      }
    }
    const requeteOriginale = error.config as RequeteAvecRetry | undefined;
    // Un 401 sur /auth/* (mauvais mot de passe, code OTP errone...) est une reponse
    // metier a afficher sur place : jamais un motif de rafraichissement ni de redirection.
    const estAppelAuth = requeteOriginale?.url?.startsWith("/auth/") ?? false;
    if (error.response?.status === 401 && requeteOriginale && !requeteOriginale._retry && !estAppelAuth) {
      requeteOriginale._retry = true;
      const nouveauToken = await rafraichirUneFois();
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
