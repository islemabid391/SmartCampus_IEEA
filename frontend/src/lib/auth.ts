import { apiFetch } from "./api";

const ACCESS_TOKEN_KEY = "smartcampus_access_token";

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export type RegisterData = {
  email: string;
  mot_de_passe: string;
  nom: string;
  prenom: string;
  consentement_rgpd: boolean;
};

export function getAccessToken(): string | null {
  try {
    return window.localStorage.getItem(ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
}

function storeAccessToken(token: string): void {
  try {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
  } catch {
    /* ignoré */
  }
}

export function logout(): void {
  try {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  } catch {
    /* ignoré */
  }
}

export async function login(email: string, mot_de_passe: string): Promise<void> {
  const token = await apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, mot_de_passe }),
  });
  storeAccessToken(token.access_token);
}

export async function register(data: RegisterData): Promise<void> {
  const token = await apiFetch<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
  storeAccessToken(token.access_token);
}