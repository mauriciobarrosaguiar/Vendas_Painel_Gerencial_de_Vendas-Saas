"use client";

import { useRef, useState } from "react";
import { apiPath } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

type UploadBaseCardProps = {
  title: string;
  description: string;
  typeBase: string;
};

type UploadState = {
  loading: boolean;
  message: string;
  tone: "muted" | "ok" | "error";
};

export function UploadBaseCard({ title, description, typeBase }: UploadBaseCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<UploadState>({
    loading: false,
    message: "Nenhum arquivo enviado.",
    tone: "muted",
  });

  async function handleUpload() {
    const file = inputRef.current?.files?.[0];
    if (!file) {
      setState({ loading: false, message: "Selecione um arquivo .xlsx, .xls ou .csv.", tone: "error" });
      return;
    }

    setState({ loading: true, message: "Enviando e validando arquivo...", tone: "muted" });

    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (!token) {
      setState({ loading: false, message: "Entre no painel antes de importar bases.", tone: "error" });
      return;
    }

    const formData = new FormData();
    formData.append("tipo_base", typeBase);
    formData.append("arquivo", file);

    try {
      const response = await fetch(apiPath("/importacao"), {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const payload = (await response.json().catch(() => ({}))) as { message?: string; detail?: string };
      if (!response.ok) {
        throw new Error(payload.detail || payload.message || "Falha ao importar arquivo.");
      }
      setState({ loading: false, message: payload.message || "Base importada com sucesso.", tone: "ok" });
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    } catch (error) {
      setState({
        loading: false,
        message: error instanceof Error ? error.message : "Falha ao importar arquivo.",
        tone: "error",
      });
    }
  }

  const toneClass =
    state.tone === "ok"
      ? "text-primary"
      : state.tone === "error"
        ? "text-[#a33a2a]"
        : "text-[#60786c]";

  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <h3 className="font-semibold text-foreground">{title}</h3>
      <p className="mt-1 text-sm text-[#60786c]">{description}</p>
      <div className="mt-4 space-y-3">
        <input
          ref={inputRef}
          className="focus-ring block w-full rounded-md border border-dashed border-border bg-muted px-3 py-3 text-sm"
          type="file"
          accept=".xlsx,.xls,.csv"
        />
        <button
          className="focus-ring rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-[#0f5838] disabled:cursor-not-allowed disabled:opacity-60"
          type="button"
          disabled={state.loading}
          onClick={handleUpload}
        >
          {state.loading ? "Importando..." : "Importar"}
        </button>
        <p className={`text-sm ${toneClass}`}>{state.message}</p>
      </div>
    </section>
  );
}
