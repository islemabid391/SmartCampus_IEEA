import { ApiError, apiFetch } from "./api";
import { getAccessToken } from "./auth";
import { clearConversationId } from "./conversation";
import { clearToken, getStoredToken } from "./session";

export type RattachementApercu = {
  rattachable: boolean;
  nb_conversations: number;
  nb_messages: number;
};

function entetes(): Record<string, string> | null {
  const jwt = getAccessToken();
  const visiteur = getStoredToken();
  if (!jwt || !visiteur) return null;
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${jwt}`,
    "X-Session-Token": visiteur,
  };
}

/** Retourne l'aperçu, ou null s'il n'y a rien à proposer (pas de session visiteur, pas connecté...). */
export async function getApercuRattachement(): Promise<RattachementApercu | null> {
  const headers = entetes();
  if (!headers) return null;
  try {
    const apercu = await apiFetch<RattachementApercu>("/sessions/me/rattachement", { headers });
    return apercu.rattachable ? apercu : null;
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return null;
    throw error;
  }
}

/** À appeler uniquement après l'accord explicite du candidat. */
export async function accepterRattachement(): Promise<number> {
  const headers = entetes();
  if (!headers) throw new Error("Connexion ou session visiteur manquante.");
  const result = await apiFetch<{ conversations_rattachees: number }>(
    "/sessions/me/rattachement",
    { method: "POST", headers, body: JSON.stringify({ consentement: true }) }
  );
  // L'ancien token visiteur est désormais mort : on l'oublie.
  clearToken();
  clearConversationId();
  return result.conversations_rattachees;
}