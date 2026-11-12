"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../src/lib/api";

export default function Home() {
  const [status, setStatus] = useState("Vérification du backend...");

  useEffect(() => {
    apiFetch<{ status: string }>("/health")
      .then((data) =>
        setStatus(data.status === "ok" ? "Backend connecté ✅" : "Réponse inattendue")
      )
      .catch(() => setStatus("Backend injoignable ❌"));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-3xl font-bold">SmartCampus AI</h1>
      <p className="text-lg">{status}</p>
    </main>
  );
}