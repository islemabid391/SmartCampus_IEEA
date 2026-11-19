import { ApiError, apiFetch } from "./api";

const TOKEN_KEY = "smartcampus_session_token";

export type SessionCreated = {
  token: string;
  date_expiration: string;
  expire_dans_secondes: number;
};

export type SessionStatus = {
  statut: string;
  date_creation: string;
  date_expiration: string;
  expire_dans_secondes: number;
  messages_restants: number;
  conversations_restantes: number;
};

// localStorage peut être indisponible (navigation privée, SSR) : on protège chaque accès.
export function getStoredToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function storeToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* ignoré : la session vivra seulement le temps de la page */
  }
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignoré */
  }
}

function withToken(token: string, options?: RequestInit): RequestInit {
  return {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers as Record<string, string> | undefined),
      "X-Session-Token": token,
    },
  };
}

/** Crée une nouvelle session côté serveur et mémorise son token. */
export async function createSession(): Promise<string> {
  const created = await apiFetch<SessionCreated>("/sessions", { method: "POST" });
  storeToken(created.token);
  return created.token;
}

export function getSessionStatus(token: string): Promise<SessionStatus> {
  return apiFetch<SessionStatus>("/sessions/me", withToken(token));
}

/**
 * Retourne un token de session valide :
 * réutilise celui du navigateur s'il est encore valable, sinon en crée un nouveau.
 */
export async function ensureSession(): Promise<string> {
  const stored = getStoredToken();
  if (stored) {
    try {
      await getSessionStatus(stored);
      return stored;
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
      clearToken(); // expirée ou inconnue : on en recrée une
    }
  }
  return createSession();
}

/** Comme apiFetch, mais avec la session visiteur (créée ou renouvelée si besoin). */
export async function sessionFetch<T>(path: string, options?: RequestInit): Promise<T> {
  let token = await ensureSession();
  try {
    return await apiFetch<T>(path, withToken(token, options));
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    clearToken(); // la session a expiré entre-temps : une seule nouvelle tentative
    token = await createSession();
    return apiFetch<T>(path, withToken(token, options));
  }
}

/** Termine volontairement la session (ex. bouton « Nouvelle conversation »). */
export async function endSession(): Promise<void> {
  const token = getStoredToken();
  if (!token) return;
  try {
    await apiFetch<void>("/sessions/me", withToken(token, { method: "DELETE" }));
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
  }
  clearToken();
}