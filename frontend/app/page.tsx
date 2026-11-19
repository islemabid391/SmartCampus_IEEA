"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../src/lib/api";
import { ensureSession, getSessionStatus } from "../src/lib/session";

export default function Home() {
  const [status, setStatus] = useState("Vérification du backend...");
  const [session, setSession] = useState("Création de la session...");

  useEffect(() => {
    apiFetch<{ status: string }>("/health")
      .then((data) =>
        setStatus(data.status === "ok" ? "Backend connecté ✅" : "Réponse inattendue")
      )
      .catch(() => setStatus("Backend injoignable ❌"));

    ensureSession()
      .then(getSessionStatus)
      .then((s) =>
        setSession(
          `Session visiteur active : expire dans ${Math.ceil(s.expire_dans_secondes / 60)} min, ` +
            `${s.messages_restants} messages restants`
        )
      )
      .catch(() => setSession("Session indisponible ❌"));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-3xl font-bold">SmartCampus AI</h1>
      <p className="text-lg">{status}</p>
      <p className="text-lg">{session}</p>
    </main>
  );
}