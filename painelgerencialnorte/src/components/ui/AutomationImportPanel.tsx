"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiPath } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

type RunSummary = {
  id: string;
  status: string;
  conclusion?: string | null;
  created_at?: string | null;
  html_url?: string | null;
};

type MercadoStatus = {
  available_ufs?: string[];
  total_eans?: number;
  tem_painel?: boolean;
  tem_produtos_mercado?: boolean;
  runs?: RunSummary[];
  runs_error?: string;
};

type BussolaStatus = {
  runs?: RunSummary[];
  runs_error?: string;
};

type AutomationState = {
  loading: boolean;
  message: string;
  tone: "muted" | "ok" | "error";
};

const initialState: AutomationState = {
  loading: false,
  message: "Pronto para disparar.",
  tone: "muted",
};

function toneClass(tone: AutomationState["tone"]) {
  if (tone === "ok") {
    return "text-primary";
  }
  if (tone === "error") {
    return "text-[#a33a2a]";
  }
  return "text-[#60786c]";
}

function latestRun(runs?: RunSummary[]) {
  return runs?.[0];
}

function runLabel(run?: RunSummary) {
  if (!run) {
    return "Nenhuma execucao recente.";
  }
  return `${run.status || "status"}${run.conclusion ? ` / ${run.conclusion}` : ""}`;
}

function errorMessage(payload: unknown, fallback: string) {
  if (payload && typeof payload === "object") {
    const data = payload as { detail?: unknown; message?: unknown };
    if (typeof data.detail === "string") {
      return data.detail;
    }
    if (typeof data.message === "string") {
      return data.message;
    }
  }
  return fallback;
}

export function AutomationImportPanel() {
  const [mercadoStatus, setMercadoStatus] = useState<MercadoStatus>({});
  const [bussolaStatus, setBussolaStatus] = useState<BussolaStatus>({});
  const [selectedUfs, setSelectedUfs] = useState<string[]>([]);
  const [limit, setLimit] = useState("0");
  const [headless, setHeadless] = useState(true);
  const [state, setState] = useState<AutomationState>(initialState);

  const mercadoRun = latestRun(mercadoStatus.runs);
  const bussolaRun = latestRun(bussolaStatus.runs);
  const availableUfs = useMemo(() => mercadoStatus.available_ufs ?? [], [mercadoStatus.available_ufs]);

  const authToken = useCallback(async () => {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? "";
  }, []);

  const refreshStatus = useCallback(async () => {
    const token = await authToken();
    if (!token) {
      setState({ loading: false, message: "Entre no painel para usar as automacoes.", tone: "error" });
      return;
    }
    const headers = { Authorization: `Bearer ${token}` };
    const [mercadoResponse, bussolaResponse] = await Promise.all([
      fetch(apiPath("/automacoes/mercado-farma"), { cache: "no-store", headers }),
      fetch(apiPath("/automacoes/bussola"), { cache: "no-store", headers }),
    ]);
    if (mercadoResponse.ok) {
      const payload = (await mercadoResponse.json()) as MercadoStatus;
      const nextUfs = payload.available_ufs ?? [];
      setMercadoStatus(payload);
      setSelectedUfs((current) => current.filter((uf) => nextUfs.includes(uf)));
    }
    if (bussolaResponse.ok) {
      setBussolaStatus((await bussolaResponse.json()) as BussolaStatus);
    }
  }, [authToken]);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  function toggleUf(uf: string) {
    setSelectedUfs((current) => (current.includes(uf) ? current.filter((item) => item !== uf) : [...current, uf]));
  }

  async function postAutomation(path: string, body: Record<string, unknown>, loadingMessage: string) {
    setState({ loading: true, message: loadingMessage, tone: "muted" });
    const token = await authToken();
    if (!token) {
      setState({ loading: false, message: "Entre no painel antes de disparar automacoes.", tone: "error" });
      return;
    }
    try {
      const response = await fetch(apiPath(path), {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = (await response.json().catch(() => ({}))) as { message?: string };
      if (!response.ok) {
        throw new Error(errorMessage(payload, "Falha ao disparar automacao."));
      }
      setState({ loading: false, message: payload.message || "Automacao disparada.", tone: "ok" });
      void refreshStatus();
    } catch (error) {
      setState({
        loading: false,
        message: error instanceof Error ? error.message : "Falha ao disparar automacao.",
        tone: "error",
      });
    }
  }

  async function extractBussola() {
    await postAutomation("/automacoes/bussola", { headless }, "Disparando extracao Bussola...");
  }

  async function updateSelectedUfs() {
    await postAutomation(
      "/automacoes/mercado-farma",
      { ufs: selectedUfs, todas_ufs: false, limite_eans: Number(limit) || 0, headless },
      "Disparando Mercado Farma para UFs selecionadas...",
    );
  }

  async function updateAllUfs() {
    await postAutomation(
      "/automacoes/mercado-farma",
      { ufs: [], todas_ufs: true, limite_eans: Number(limit) || 0, headless },
      "Disparando Mercado Farma para todas as UFs...",
    );
  }

  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="font-semibold text-foreground">Automacoes web</h3>
          <p className="mt-1 text-sm text-[#60786c]">
            Dispare as extracoes automaticas pelo GitHub Actions e publique a base final no Supabase.
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm text-[#355242]">
          <input checked={headless} type="checkbox" onChange={(event) => setHeadless(event.target.checked)} />
          Rodar navegador oculto
        </label>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div className="space-y-3">
          <div>
            <h4 className="font-medium text-foreground">Bussola Web</h4>
            <p className="mt-1 text-sm text-[#60786c]">
              Usa GD quando configurado; caso contrario, usa consultores marcados com login completo.
            </p>
          </div>
          <button
            className="focus-ring rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-[#0f5838] disabled:cursor-not-allowed disabled:opacity-60"
            type="button"
            disabled={state.loading}
            onClick={extractBussola}
          >
            Extrair Bussola agora
          </button>
          <p className="text-sm text-[#60786c]">
            Ultimo run:{" "}
            {bussolaRun?.html_url ? (
              <a className="font-medium text-primary underline" href={bussolaRun.html_url} target="_blank" rel="noreferrer">
                {runLabel(bussolaRun)}
              </a>
            ) : (
              runLabel(bussolaRun)
            )}
          </p>
          {bussolaStatus.runs_error ? <p className="text-sm text-[#a33a2a]">{bussolaStatus.runs_error}</p> : null}
        </div>

        <div className="space-y-3">
          <div>
            <h4 className="font-medium text-foreground">Mercado Farma por UF</h4>
            <p className="mt-1 text-sm text-[#60786c]">
              UFs detectadas pela base de clientes ativa. EANs na lista: {mercadoStatus.total_eans ?? 0}.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {availableUfs.length ? (
              availableUfs.map((uf) => (
                <label
                  key={uf}
                  className="flex items-center gap-2 rounded-md border border-border bg-muted px-3 py-2 text-sm text-[#355242]"
                >
                  <input checked={selectedUfs.includes(uf)} type="checkbox" onChange={() => toggleUf(uf)} />
                  {uf}
                </label>
              ))
            ) : (
              <p className="text-sm text-[#a33a2a]">Importe Painel clientes com UF/CNPJ ativo para listar as UFs.</p>
            )}
          </div>
          <label className="block text-sm font-medium text-[#355242]">
            Limite de EANs para teste
            <input
              className="focus-ring mt-1 block w-32 rounded-md border border-border bg-muted px-3 py-2 text-sm"
              min="0"
              type="number"
              value={limit}
              onChange={(event) => setLimit(event.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              className="focus-ring rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-[#0f5838] disabled:cursor-not-allowed disabled:opacity-60"
              type="button"
              disabled={state.loading || selectedUfs.length === 0}
              onClick={updateSelectedUfs}
            >
              Atualizar UFs selecionadas
            </button>
            <button
              className="focus-ring rounded-md border border-primary px-4 py-2 text-sm font-semibold text-primary hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
              type="button"
              disabled={state.loading || availableUfs.length === 0}
              onClick={updateAllUfs}
            >
              Atualizar todas as UFs
            </button>
          </div>
          <p className="text-sm text-[#60786c]">
            Ultimo run:{" "}
            {mercadoRun?.html_url ? (
              <a className="font-medium text-primary underline" href={mercadoRun.html_url} target="_blank" rel="noreferrer">
                {runLabel(mercadoRun)}
              </a>
            ) : (
              runLabel(mercadoRun)
            )}
          </p>
          {mercadoStatus.runs_error ? <p className="text-sm text-[#a33a2a]">{mercadoStatus.runs_error}</p> : null}
        </div>
      </div>
      <p className={`mt-4 text-sm ${toneClass(state.tone)}`}>{state.message}</p>
    </section>
  );
}
