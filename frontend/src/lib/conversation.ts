import { ApiError } from "./api";
import { sessionFetch } from "./session";

const CONVERSATION_KEY = "smartcampus_conversation_id";

export type Conversation = {
  id: number;
  langue_detectee: string | null;
  date_creation: string;
};

export type Message = {
  id: number;
  role: "user" | "assistant" | "system";
  contenu: string;
  langue: string | null;
  date_creation: string;
  date_expiration: string | null;
};

export type Memoire = {
  informations: Record<string, unknown>;
  infos_manquantes: string[];
};

function getStoredConversationId(): number | null {
  try {
    const value = window.localStorage.getItem(CONVERSATION_KEY);
    return value ? Number(value) : null;
  } catch {
    return null;
  }
}

function storeConversationId(id: number): void {
  try {
    window.localStorage.setItem(CONVERSATION_KEY, String(id));
  } catch {
    /* ignoré */
  }
}

export function clearConversationId(): void {
  try {
    window.localStorage.removeItem(CONVERSATION_KEY);
  } catch {
    /* ignoré */
  }
}

export function createConversation(langue?: string): Promise<Conversation> {
  const query = langue ? `?langue=${encodeURIComponent(langue)}` : "";
  return sessionFetch<Conversation>(`/conversations${query}`, { method: "POST" });
}

export function getMessages(conversationId: number, limite?: number): Promise<Message[]> {
  const query = limite ? `?limite=${limite}` : "";
  return sessionFetch<Message[]>(`/conversations/${conversationId}/messages${query}`);
}

export function sendMessage(
  conversationId: number,
  contenu: string,
  langue?: string
): Promise<Message> {
  return sessionFetch<Message>(`/conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify({ contenu, langue }),
  });
}

export function getMemoire(conversationId: number): Promise<Memoire> {
  return sessionFetch<Memoire>(`/conversations/${conversationId}/memoire`);
}

/** Droit à l'oubli : supprime les messages et les informations retenues. */
export function forgetConversation(conversationId: number): Promise<void> {
  return sessionFetch<void>(`/conversations/${conversationId}/memoire`, { method: "DELETE" });
}

/**
 * Retourne l'identifiant de la conversation en cours : réutilise celle du navigateur
 * si elle existe encore pour la session, sinon en ouvre une nouvelle.
 */
export async function ensureConversation(langue?: string): Promise<number> {
  const stored = getStoredConversationId();
  if (stored) {
    try {
      await getMessages(stored, 1);
      return stored;
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 404) throw error;
      clearConversationId(); // session renouvelée ou conversation supprimée
    }
  }
  const conversation = await createConversation(langue);
  storeConversationId(conversation.id);
  return conversation.id;
}