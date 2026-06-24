import type { DashboardSnapshot } from "./types";
import { formatCurrency, formatInteger, formatPercent } from "./formatters";

type DashboardApiResponse = {
  ok?: boolean;
  available?: boolean;
  empty?: boolean;
  api_connected?: boolean;
  supabase_connected?: boolean;
  message?: string;
  indicadores?: {
    ol_sem_combate?: number;
    ol_prioritarios?: number;
    percentual_prioritarios?: number;
    ol_lancamentos?: number;
    percentual_lancamentos?: number;
    quantidade_pedidos?: number;
    ticket_medio?: number;
    clientes_positivados?: number;
    clientes_sem_compra?: number;
    clientes_ativos?: number;
    positivacao_percentual?: number;
  };
  resumo_operacional?: {
    pedidos_faturados?: number;
    valor_pedidos_faturados?: number;
    pedidos_sem_nota?: number;
    valor_sem_nota?: number;
    pedidos_cancelados?: number;
    valor_cancelado?: number;
  };
  bases?: Array<{
    name: string;
    type: string;
    updatedAt: string;
    source: string;
    status: "ok" | "missing" | "invalid";
  }>;
};

const EMPTY_MESSAGE = "Nenhuma base importada ainda";

const EMPTY_SNAPSHOT: DashboardSnapshot = {
  available: false,
  empty: true,
  apiConnected: false,
  supabaseConnected: false,
  message: EMPTY_MESSAGE,
  metrics: [
    { label: "OL sem combate", value: "-", detail: "Aguardando base Bussola" },
    { label: "OL prioritarios", value: "-", detail: "Aguardando Produtos / Mix" },
    { label: "OL lancamentos", value: "-", detail: "Aguardando Produtos / Mix" },
    { label: "Clientes com venda", value: "-", detail: "Aguardando Painel clientes" },
  ],
  operational: [
    { label: "Pedidos faturados", value: "-", detail: EMPTY_MESSAGE },
    { label: "Pedidos sem nota", value: "-", detail: EMPTY_MESSAGE },
    { label: "Cancelados", value: "-", detail: EMPTY_MESSAGE },
    { label: "Valor sem nota", value: "-", detail: EMPTY_MESSAGE },
  ],
  bases: [
    { name: "Bussola", type: "bussola", updatedAt: "-", source: "Supabase Storage", status: "missing" },
    { name: "Painel clientes", type: "painel", updatedAt: "-", source: "Supabase Storage", status: "missing" },
    { name: "Produtos / Mix", type: "produtos_mix", updatedAt: "-", source: "Supabase Storage", status: "missing" },
  ],
};

export function apiPath(path: string): string {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL || "/api";
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  if (base.startsWith("http")) {
    return new URL(cleanPath.replace(/^\//, ""), base.endsWith("/") ? base : `${base}/`).toString();
  }
  return `${base.replace(/\/$/, "")}${cleanPath}`;
}

function snapshotFromApi(payload: DashboardApiResponse): DashboardSnapshot {
  const baseSnapshot: DashboardSnapshot = {
    ...EMPTY_SNAPSHOT,
    apiConnected: Boolean(payload.api_connected ?? payload.ok),
    supabaseConnected: Boolean(payload.supabase_connected),
    message: payload.message ?? EMPTY_MESSAGE,
    bases: payload.bases?.length ? payload.bases : EMPTY_SNAPSHOT.bases,
  };

  if (payload.empty || !payload.available || !payload.indicadores || !payload.resumo_operacional) {
    return baseSnapshot;
  }

  const indicadores = payload.indicadores;
  const resumo = payload.resumo_operacional;
  return {
    available: true,
    empty: false,
    apiConnected: true,
    supabaseConnected: Boolean(payload.supabase_connected),
    message: payload.message ?? "API conectada",
    metrics: [
      { label: "OL sem combate", value: formatCurrency(indicadores.ol_sem_combate ?? 0), detail: "Faturado sem COMBATE" },
      {
        label: "OL prioritarios",
        value: formatCurrency(indicadores.ol_prioritarios ?? 0),
        detail: formatPercent(indicadores.percentual_prioritarios ?? 0),
      },
      {
        label: "OL lancamentos",
        value: formatCurrency(indicadores.ol_lancamentos ?? 0),
        detail: formatPercent(indicadores.percentual_lancamentos ?? 0),
      },
      {
        label: "Clientes com venda",
        value: formatInteger(indicadores.clientes_positivados ?? 0),
        detail: formatPercent(indicadores.positivacao_percentual ?? 0),
      },
    ],
    operational: [
      { label: "Pedidos faturados", value: formatInteger(resumo.pedidos_faturados ?? 0), detail: formatCurrency(resumo.valor_pedidos_faturados ?? 0) },
      { label: "Pedidos sem nota", value: formatInteger(resumo.pedidos_sem_nota ?? 0), detail: formatCurrency(resumo.valor_sem_nota ?? 0) },
      { label: "Cancelados", value: formatInteger(resumo.pedidos_cancelados ?? 0), detail: formatCurrency(resumo.valor_cancelado ?? 0) },
      { label: "Ticket medio", value: formatCurrency(indicadores.ticket_medio ?? 0), detail: `${formatInteger(indicadores.quantidade_pedidos ?? 0)} pedidos` },
    ],
    bases: payload.bases?.length ? payload.bases : EMPTY_SNAPSHOT.bases,
  };
}

export async function getApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(apiPath("/health"), { cache: "no-store" });
    const payload = (await response.json()) as { ok?: boolean };
    return Boolean(response.ok && payload.ok);
  } catch {
    return false;
  }
}

export async function getDashboardSnapshot(token?: string): Promise<DashboardSnapshot> {
  try {
    const response = await fetch(apiPath("/dashboard"), {
      cache: "no-store",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    if (!response.ok) {
      return {
        ...EMPTY_SNAPSHOT,
        apiConnected: response.status !== 500,
        message: "Falha ao carregar dados. Verifique configuracao da API/Supabase.",
      };
    }
    const payload = (await response.json()) as DashboardApiResponse;
    return snapshotFromApi(payload);
  } catch {
    return {
      ...EMPTY_SNAPSHOT,
      message: "Falha ao carregar dados. Verifique configuracao da API/Supabase.",
    };
  }
}
