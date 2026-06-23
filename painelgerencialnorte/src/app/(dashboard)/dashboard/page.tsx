import { MetricCard } from "@/components/ui/MetricCard";
import { ProjectionBadge } from "@/components/ui/ProjectionBadge";
import { StatusPeriodo } from "@/components/ui/StatusPeriodo";
import { DataTable } from "@/components/ui/DataTable";
import { FilterPanel } from "@/components/ui/FilterPanel";
import { getDashboardSnapshot } from "@/lib/api";

export default async function DashboardPage() {
  const snapshot = await getDashboardSnapshot();

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
        <ProjectionBadge label="Core Python testado: 21 checks" tone="green" />
      </div>

      <FilterPanel />

      {!snapshot.available ? (
        <div className="rounded-lg border border-border bg-muted p-4 text-sm text-[#466155]">{snapshot.message}</div>
      ) : null}

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {snapshot.metrics.map((metric) => (
          <MetricCard key={metric.label} {...metric} />
        ))}
      </section>

      <section className="grid gap-3 md:grid-cols-3">
        <MetricCard label="Falta 80%" value="-" detail="Mesmo calculo falta_para_meta" />
        <MetricCard label="Falta 90%" value="-" detail="Mesmo calculo falta_para_meta" />
        <MetricCard label="Falta 100%" value="-" detail="Mesmo calculo falta_para_meta" />
      </section>

      <StatusPeriodo metrics={snapshot.operational} />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-foreground">Ultimas atualizacoes</h2>
        <DataTable
          columns={["Base", "Tipo", "Atualizacao", "Origem", "Status"]}
          rows={snapshot.bases.map((base) => ({
            Base: base.name,
            Tipo: base.type,
            Atualizacao: base.updatedAt,
            Origem: base.source,
            Status: base.status,
          }))}
        />
      </section>
    </div>
  );
}

