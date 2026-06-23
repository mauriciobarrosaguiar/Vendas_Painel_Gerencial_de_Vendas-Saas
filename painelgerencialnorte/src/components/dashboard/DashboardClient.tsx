"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/ui/DataTable";
import { FilterPanel } from "@/components/ui/FilterPanel";
import { MetricCard } from "@/components/ui/MetricCard";
import { ProjectionBadge } from "@/components/ui/ProjectionBadge";
import { StatusPeriodo } from "@/components/ui/StatusPeriodo";
import { getApiHealth, getDashboardSnapshot } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import type { DashboardSnapshot } from "@/lib/types";

type LoadState = {
  loading: boolean;
  snapshot: DashboardSnapshot | null;
};

export function DashboardClient() {
  const [state, setState] = useState<LoadState>({ loading: true, snapshot: null });

  useEffect(() => {
    let active = true;

    async function load() {
      const supabase = createClient();
      const [{ data }, apiConnected] = await Promise.all([supabase.auth.getSession(), getApiHealth()]);
      const token = data.session?.access_token;
      const snapshot = await getDashboardSnapshot(token);
      if (active) {
        setState({
          loading: false,
          snapshot: { ...snapshot, apiConnected: snapshot.apiConnected || apiConnected },
        });
      }
    }

    load().catch(() => {
      if (active) {
        setState({ loading: false, snapshot: null });
      }
    });

    return () => {
      active = false;
    };
  }, []);

  const snapshot = state.snapshot;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Dashboard</h2>
          <p className="mt-1 max-w-3xl text-sm text-[#60786c]">
            Substitui a Visao Geral do Streamlit, mantendo OL sem combate, prioritarios, lancamentos, clientes com venda,
            metas, faltas e projecao.
          </p>
        </div>
        <ProjectionBadge label="Core Python testado" tone="green" />
      </div>

      <FilterPanel />

      <div className="flex flex-wrap gap-2 text-sm">
        <span className={`rounded-md border px-3 py-2 ${snapshot?.apiConnected ? "border-[#b6d7c3] bg-[#edf8f1] text-primary" : "border-border bg-muted text-[#60786c]"}`}>
          {snapshot?.apiConnected ? "API conectada" : state.loading ? "Verificando API..." : "API indisponivel"}
        </span>
        <span className={`rounded-md border px-3 py-2 ${snapshot?.supabaseConnected ? "border-[#b6d7c3] bg-[#edf8f1] text-primary" : "border-border bg-muted text-[#60786c]"}`}>
          {snapshot?.supabaseConnected ? "Supabase conectado" : state.loading ? "Verificando Supabase..." : "Supabase nao conectado"}
        </span>
      </div>

      {state.loading ? (
        <div className="rounded-lg border border-border bg-muted p-4 text-sm text-[#466155]">Carregando status do painel...</div>
      ) : null}

      {!state.loading && !snapshot ? (
        <div className="rounded-lg border border-border bg-muted p-4 text-sm text-[#466155]">
          Falha ao carregar dados. Verifique configuracao da API/Supabase.
        </div>
      ) : null}

      {snapshot?.message ? (
        <div className="rounded-lg border border-border bg-muted p-4 text-sm text-[#466155]">{snapshot.message}</div>
      ) : null}

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {(snapshot?.metrics ?? []).map((metric) => (
          <MetricCard key={metric.label} {...metric} />
        ))}
      </section>

      <section className="grid gap-3 md:grid-cols-3">
        <MetricCard label="Falta 80%" value="-" detail="Mesmo calculo falta_para_meta" />
        <MetricCard label="Falta 90%" value="-" detail="Mesmo calculo falta_para_meta" />
        <MetricCard label="Falta 100%" value="-" detail="Mesmo calculo falta_para_meta" />
      </section>

      <StatusPeriodo metrics={snapshot?.operational ?? []} />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-foreground">Ultimas atualizacoes</h2>
        <DataTable
          columns={["Base", "Tipo", "Atualizacao", "Origem", "Status"]}
          rows={(snapshot?.bases ?? []).map((base) => ({
            Base: base.name,
            Tipo: base.type,
            Atualizacao: base.updatedAt,
            Origem: base.source,
            Status: base.status,
          }))}
          emptyText="Nenhuma base importada ainda."
        />
      </section>
    </div>
  );
}
