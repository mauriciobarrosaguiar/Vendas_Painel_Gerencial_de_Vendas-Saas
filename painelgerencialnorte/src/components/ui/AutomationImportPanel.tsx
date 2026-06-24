"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiPath } from "@/lib/api";

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
  tem_produtos_mix?: boolean;
  tem_produtos_mercado?: boolean;
  vendedores_gd?: GdVendedor[];
  runs?: RunSummary[];
  runs_error?: string;
};

type GdVendedor = {
  gd: string;
  setor: string;
  vendedor: string;
  ufs: string[];
  clientes_ativos: number;
  total_vendedores_gd: number;
  total_clientes_gd: number;
};

type BussolaStatus = {
  runs?: RunSummary[];
  runs_error?: string;
};

type CredentialStatus = {
  encryption_configured?: boolean;
  bussola?: {
    gd_usuario?: string;
    gd_usuario_mascarado?: string;
    tem_senha?: boolean;
    usar_gd?: boolean;
    headless?: boolean;
  };
  mercado_farma?: {
    usuario?: string;
    usuario_mascarado?: string;
    tem_senha?: boolean;
  };
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

async function responsePayload(response: Response): Promise<{ detail?: unknown; message?: unknown; raw?: string }> {
  const text = await response.text().catch(() => "");
  if (!text) {
    return {};
  }
  try {
    return { ...(JSON.parse(text) as object), raw: text };
  } catch {
    return { raw: text };
  }
}

function errorMessage(payload: unknown, fallback: string) {
  if (payload && typeof payload === "object") {
    const data = payload as { detail?: unknown; message?: unknown; raw?: unknown };
    if (typeof data.detail === "string" && data.detail.trim()) {
      return data.detail;
    }
    if (typeof data.message === "string" && data.message.trim()) {
      return data.message;
    }
    if (typeof data.raw === "string" && data.raw.trim()) {
      return data.raw.slice(0, 500);
    }
  }
  return fallback;
}

export function AutomationImportPanel() {
  const [mercadoStatus, setMercadoStatus] = useState<MercadoStatus>({});
  const [bussolaStatus, setBussolaStatus] = useState<BussolaStatus>({});
  const [credentialStatus, setCredentialStatus] = useState<CredentialStatus>({});
  const [bussolaLogin, setBussolaLogin] = useState({ usuario: "", senha: "" });
  const [mercadoLogin, setMercadoLogin] = useState({ usuario: "", senha: "" });
  const [selectedUfs, setSelectedUfs] = useState<string[]>([]);
  const [limit, setLimit] = useState("0");
  const [headless, setHeadless] = useState(true);
  const [usarGd, setUsarGd] = useState(true);
  const [state, setState] = useState<AutomationState>(initialState);

  const mercadoRun = latestRun(mercadoStatus.runs);
  const bussolaRun = latestRun(bussolaStatus.runs);
  const availableUfs = useMemo(() => mercadoStatus.available_ufs ?? [], [mercadoStatus.available_ufs]);
  const vendedoresGd = mercadoStatus.vendedores_gd ?? [];
  const missingPainel = mercadoStatus.tem_painel === false;
  const missingProdutosMix = mercadoStatus.tem_produtos_mix === false || (!mercadoStatus.tem_produtos_mix && (mercadoStatus.total_eans ?? 0) === 0);

  const authToken = useCallback(async () => {
    return "";
  }, []);

  const refreshStatus = useCallback(async () => {
    const token = await authToken();
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
    const [mercadoResponse, bussolaResponse, credentialsResponse] = await Promise.all([
      fetch(apiPath("/automacoes/mercado-farma"), { cache: "no-store", headers }),
      fetch(apiPath("/automacoes/bussola"), { cache: "no-store", headers }),
      fetch(apiPath("/automacoes/credenciais"), { cache: "no-store", headers }),
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
    if (credentialsResponse.ok) {
      const payload = (await credentialsResponse.json()) as CredentialStatus;
      setCredentialStatus(payload);
      setBussolaLogin((current) => ({ ...current, usuario: payload.bussola?.gd_usuario ?? current.usuario }));
      setMercadoLogin((current) => ({ ...current, usuario: payload.mercado_farma?.usuario ?? current.usuario }));
      setUsarGd(Boolean(payload.bussola?.usar_gd ?? true));
      setHeadless(Boolean(payload.bussola?.headless ?? true));
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
    const headers = new Headers({ "Content-Type": "application/json" });
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    try {
      const response = await fetch(apiPath(path), {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });
      const payload = await responsePayload(response);
      if (!response.ok) {
        throw new Error(errorMessage(payload, `Falha ao disparar automacao. HTTP ${response.status}`));
      }
      setState({ loading: false, message: String(payload.message || "Automacao disparada."), tone: "ok" });
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

  async function saveCredentials() {
    await postAutomation(
      "/automacoes/credenciais",
      {
        bussola: {
          gd_usuario: bussolaLogin.usuario,
          gd_senha: bussolaLogin.senha,
          usar_gd: usarGd,
          headless,
        },
        mercado_farma: {
          usuario: mercadoLogin.usuario,
          senha: mercadoLogin.senha,
        },
      },
      "Salvando credenciais...",
    );
    setBussolaLogin((current) => ({ ...current, senha: "" }));
    setMercadoLogin((current) => ({ ...current, senha: "" }));
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
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="block text-sm font-medium text-[#355242]">
              Login / e-mail GD
              <input
                className="focus-ring mt-1 block w-full rounded-md border border-border bg-muted px-3 py-2 text-sm"
                type="text"
                value={bussolaLogin.usuario}
                onChange={(event) => setBussolaLogin((current) => ({ ...current, usuario: event.target.value }))}
              />
            </label>
            <label className="block text-sm font-medium text-[#355242]">
              Senha GD
              <input
                className="focus-ring mt-1 block w-full rounded-md border border-border bg-muted px-3 py-2 text-sm"
                placeholder={credentialStatus.bussola?.tem_senha ? "Senha ja salva" : ""}
                type="password"
                value={bussolaLogin.senha}
                onChange={(event) => setBussolaLogin((current) => ({ ...current, senha: event.target.value }))}
              />
            </label>
          </div>
          <label className="flex items-center gap-2 text-sm text-[#355242]">
            <input checked={usarGd} type="checkbox" onChange={(event) => setUsarGd(event.target.checked)} />
            Usar GD para baixar a base completa
          </label>
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
            {missingProdutosMix ? (
              <p className="mt-1 text-sm text-[#a33a2a]">Importe Produtos / Mix para gerar lista de EANs.</p>
            ) : null}
            {missingPainel ? (
              <p className="mt-1 text-sm text-[#a33a2a]">Importe Painel clientes para listar UFs.</p>
            ) : null}
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="block text-sm font-medium text-[#355242]">
              Login / e-mail GD
              <input
                className="focus-ring mt-1 block w-full rounded-md border border-border bg-muted px-3 py-2 text-sm"
                type="text"
                value={mercadoLogin.usuario}
                onChange={(event) => setMercadoLogin((current) => ({ ...current, usuario: event.target.value }))}
              />
            </label>
            <label className="block text-sm font-medium text-[#355242]">
              Senha GD
              <input
                className="focus-ring mt-1 block w-full rounded-md border border-border bg-muted px-3 py-2 text-sm"
                placeholder={credentialStatus.mercado_farma?.tem_senha ? "Senha ja salva" : ""}
                type="password"
                value={mercadoLogin.senha}
                onChange={(event) => setMercadoLogin((current) => ({ ...current, senha: event.target.value }))}
              />
            </label>
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
              <p className="text-sm text-[#a33a2a]">Importe Painel clientes para listar UFs.</p>
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
              disabled={state.loading || selectedUfs.length === 0 || missingProdutosMix || missingPainel}
              onClick={updateSelectedUfs}
            >
              Atualizar UFs selecionadas
            </button>
            <button
              className="focus-ring rounded-md border border-primary px-4 py-2 text-sm font-semibold text-primary hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
              type="button"
              disabled={state.loading || availableUfs.length === 0 || missingProdutosMix || missingPainel}
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

      <div className="mt-5 border-t border-border pt-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h4 className="font-medium text-foreground">GD e vendedores ativos</h4>
            <p className="mt-1 text-sm text-[#60786c]">
              Visao gerada pela base Painel clientes para separar resultados por setor e vendedor.
            </p>
          </div>
          <p className="text-sm text-[#60786c]">{vendedoresGd.length} vendedor(es) ativo(s)</p>
        </div>
        <div className="mt-3 overflow-hidden rounded-md border border-border">
          <div className="max-h-72 overflow-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-muted text-xs uppercase tracking-[0.08em] text-[#5f786c]">
                <tr>
                  <th className="px-3 py-2 font-semibold">GD</th>
                  <th className="px-3 py-2 font-semibold">Setor</th>
                  <th className="px-3 py-2 font-semibold">Vendedor</th>
                  <th className="px-3 py-2 font-semibold">UF(s)</th>
                  <th className="px-3 py-2 text-right font-semibold">Clientes ativos</th>
                </tr>
              </thead>
              <tbody>
                {vendedoresGd.length ? (
                  vendedoresGd.map((item) => (
                    <tr key={`${item.gd}-${item.setor}-${item.vendedor}`} className="border-t border-border">
                      <td className="px-3 py-2 text-[#183b2d]">
                        <span className="font-medium">{item.gd}</span>
                        <span className="block text-xs text-[#60786c]">
                          {item.total_vendedores_gd} vend. / {item.total_clientes_gd} clientes
                        </span>
                      </td>
                      <td className="px-3 py-2 text-[#183b2d]">{item.setor}</td>
                      <td className="px-3 py-2 text-[#183b2d]">{item.vendedor}</td>
                      <td className="px-3 py-2 text-[#183b2d]">{item.ufs?.join(", ") || "-"}</td>
                      <td className="px-3 py-2 text-right text-[#183b2d]">{item.clientes_ativos}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="px-3 py-6 text-center text-[#60786c]" colSpan={5}>
                      Importe Painel clientes para montar a visao de GD e vendedores.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-border pt-4">
        <button
          className="focus-ring rounded-md border border-primary px-4 py-2 text-sm font-semibold text-primary hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
          type="button"
          disabled={state.loading}
          onClick={saveCredentials}
        >
          Salvar logins
        </button>
        <p className="text-sm text-[#60786c]">
          As senhas ficam criptografadas. Campo de senha vazio mantem a senha salva.
        </p>
      </div>
      <p className={`mt-4 text-sm ${toneClass(state.tone)}`}>{state.message}</p>
    </section>
  );
}
