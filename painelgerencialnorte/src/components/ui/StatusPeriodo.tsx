import type { DashboardMetric } from "@/lib/types";
import { MetricCard } from "./MetricCard";

export function StatusPeriodo({ metrics }: { metrics: DashboardMetric[] }) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-semibold text-foreground">Status operacional</h2>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <MetricCard key={metric.label} {...metric} />
        ))}
      </div>
    </section>
  );
}

