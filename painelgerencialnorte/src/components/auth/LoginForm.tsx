"use client";

import { FormEvent, useState } from "react";
import { createClient } from "@/lib/supabase/client";

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (error) {
      setMessage("Nao foi possivel entrar. Confira email e senha.");
      return;
    }
    window.location.href = "/dashboard";
  }

  return (
    <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
      <label className="block text-sm">
        <span className="mb-1 block font-medium text-[#5f786c]">Email</span>
        <input
          className="focus-ring w-full rounded-md border border-border px-3 py-2"
          type="email"
          placeholder="usuario@empresa.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
      </label>
      <label className="block text-sm">
        <span className="mb-1 block font-medium text-[#5f786c]">Senha</span>
        <input
          className="focus-ring w-full rounded-md border border-border px-3 py-2"
          type="password"
          placeholder="Sua senha"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
      </label>
      <button
        className="focus-ring w-full rounded-md bg-primary px-4 py-2 font-semibold text-white hover:bg-[#0f5838] disabled:cursor-not-allowed disabled:opacity-60"
        type="submit"
        disabled={loading}
      >
        {loading ? "Entrando..." : "Entrar"}
      </button>
      {message ? <p className="text-sm text-[#a33a2a]">{message}</p> : null}
    </form>
  );
}
