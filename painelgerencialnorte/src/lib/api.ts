import type { DashboardSnapshot } from "./types";
import { formatCurrency, formatInteger, formatPercent } from "./formatters";

type DashboardApiResponse = {
  available: boolean;
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
};

const FALLBACK_SNAPSHOT: DashboardSnapshot = {
  available: false,
  message: "APIs Python e Supabase ainda nao configurados nesta etapa. O backend/core ja preserva os calculos e esta coberto por testes.",
  metrics: [
    { label: "OL sem combate", value: "-", detail: "Calculado por backend/core.calculos" },
    { label: "OL prioritarios", value: "-", detail: "Mesmo criterio do Streamlit" },
    { label: "OL lancamentos", value: "-", detail: "Mesmo criterio do Streamlit" },
    { label: "Clientes com venda", value: "-", detail: "CNPJ unico com OL sem combate > 0" },
  ],
  operational: [
    { label: "Pedidos faturados", value: "-", detail: "STATUS_FATURADOS" },
    { label: "Pedidos sem nota", value: "-", detail: "nota_fiscal vazia e nao cancelado" },
    { label: "Cancelados", value: "-", detail: "STATUS_CANCELADO" },
    { label: "Valor sem nota", value: "-", detail: "valor_total_solicitado_sem_imposto" },
  ],
  bases: [
    { name: "Bussola", type: "bussola", updatedAt: "-", source: "Supabase Storage", status: "missing" },
    { name: "Painel clientes", type: "painel", updatedAt: "-", source: "Supabase Storage", status: "missing" },
    { name: "Produtos / Mix", type: "produtos_mix", updatedAt: "-", source: "Supabase Storage", status: "missing" },
  ],
};

function getBackendUrl(path: string): string | null {
  const base = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_BACKEND_URL;
  if (!base || base.startsWith("/")) {
    return null;
  }
  return new URL(path.replace(/^\//, ""), base.endsWith("/") ? base : `${base}/`).toString();
}

function snapshotFromApi(payload: DashboardApiResponse): DashboardSnapshot {
  if (!payload.available || !payload.indicadores || !payload.resumo_operacional) {
    return { ...FALLBACK_SNAPSHOT, message: payload.message ?? FALLBACK_SNAPSHOT.message };
  }

  const indicadores = payload.indicadores;
  const resumo = payload.resumo_operacional;
  return {
    available: true,
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
    bases: [
      { name: "Bussola", type: "bussola", updatedAt: "API", source: "Backend Python", status: "ok" },
      { name: "Painel clientes", type: "painel", updatedAt: "API", source: "Backend Python", status: "ok" },
      { name: "Produtos / Mix", type: "produtos_mix", updatedAt: "API", source: "Backend Python", status: "ok" },
    ],
  };
}

export async function getDashboardSnapshot(): Promise<DashboardSnapshot> {
  const dashboardUrl = getBackendUrl("/dashboard");
  if (!dashboardUrl) {
    return FALLBACK_SNAPSHOT;
  }

  try {
    const response = await fetch(dashboardUrl, { cache: "no-store" });
    const payload = (await response.json()) as DashboardApiResponse;
    return snapshotFromApi(payload);
  } catch {
    return FALLBACK_SNAPSHOT;
  }
}
