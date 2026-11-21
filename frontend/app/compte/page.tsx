"use client";

import { useState } from "react";
import { login, register } from "../../src/lib/auth";
import {
  accepterRattachement,
  getApercuRattachement,
  type RattachementApercu,
} from "../../src/lib/rattachement";

export default function ComptePage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [nom, setNom] = useState("");
  const [prenom, setPrenom] = useState("");
  const [rgpd, setRgpd] = useState(false);
  const [message, setMessage] = useState("");
  const [apercu, setApercu] = useState<RattachementApercu | null>(null);
  const [accord, setAccord] = useState(false);

  async function soumettre(e: React.FormEvent) {
    e.preventDefault();
    setMessage("");
    try {
      if (mode === "login") {
        await login(email, motDePasse);
      } else {
        await register({
          email, mot_de_passe: motDePasse, nom, prenom, consentement_rgpd: rgpd,
        });
      }
           const proposition = await getApercuRattachement();
      setApercu(proposition);
      setMessage(
        proposition
          ? "Connecté ✅"
          : "Connecté ✅ (aucune conversation invitée à associer)"
      );
    } catch {
      setMessage("Échec : vérifiez vos informations.");
    }
  }

  async function associer() {
    try {
      const n = await accepterRattachement();
      setMessage(`${n} conversation(s) associée(s) à votre compte ✅`);
      setApercu(null);
    } catch {
      setMessage("Impossible d'associer la conversation (session expirée ?).");
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-4 p-6">
      <h1 className="text-2xl font-bold">
        {mode === "login" ? "Se connecter" : "Créer un compte"}
      </h1>

      <form onSubmit={soumettre} className="flex flex-col gap-3">
        {mode === "register" && (
          <>
            <input className="rounded border p-2" placeholder="Nom" value={nom}
                   onChange={(e) => setNom(e.target.value)} required />
            <input className="rounded border p-2" placeholder="Prénom" value={prenom}
                   onChange={(e) => setPrenom(e.target.value)} required />
          </>
        )}
        <input className="rounded border p-2" type="email" placeholder="Email" value={email}
               onChange={(e) => setEmail(e.target.value)} required />
        <input className="rounded border p-2" type="password" placeholder="Mot de passe (8 caractères min.)"
               value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} required />
        {mode === "register" && (
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={rgpd} onChange={(e) => setRgpd(e.target.checked)} />
            J&apos;accepte le traitement de mes données personnelles
          </label>
        )}
        <button className="rounded bg-blue-600 p-2 text-white" type="submit"
                disabled={mode === "register" && !rgpd}>
          {mode === "login" ? "Se connecter" : "Créer mon compte"}
        </button>
      </form>

      <button className="text-sm underline"
              onClick={() => setMode(mode === "login" ? "register" : "login")}>
        {mode === "login" ? "Pas de compte ? Créer un compte" : "Déjà un compte ? Se connecter"}
      </button>

      {message && <p>{message}</p>}

      {apercu && (
        <div className="rounded border p-4">
          <p className="font-semibold">Retrouver votre conversation</p>
          <p className="text-sm">
            Vous avez {apercu.nb_conversations} conversation(s) en cours ({apercu.nb_messages} message(s)).
            Voulez-vous les associer à votre compte pour les conserver ?
          </p>
          <label className="mt-2 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={accord} onChange={(e) => setAccord(e.target.checked)} />
            J&apos;accepte d&apos;associer cette conversation à mon compte
          </label>
          <div className="mt-3 flex gap-2">
            <button className="rounded bg-green-600 p-2 text-white" disabled={!accord} onClick={associer}>
              Associer
            </button>
            <button className="rounded border p-2" onClick={() => setApercu(null)}>
              Non merci
            </button>
          </div>
        </div>
      )}
    </main>
  );
}