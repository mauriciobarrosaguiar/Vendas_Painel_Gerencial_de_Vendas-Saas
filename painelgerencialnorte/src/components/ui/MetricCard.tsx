import type { MetricStatus } from "@/lib/types";

type MetricCardProps = {
  label: string;
  value: string;
  detail?: string;
  status?: MetricStatus;
};

const statusClass: Record<MetricStatus, string> = {
  ok: "border-primary/25 bg-white",
  warning: "border-[#d69e2e]/35 bg-[#fffaf0]",
  danger: "border-[#c53030]/30 bg-[#fff5f5]",
  muted: "border-border bg-white",
};

export function MetricCard({ label, value, detail, status = "muted" }: MetricCardProps) {
  return (
    <section className={`rounded-lg border p-4 shadow-sm ${statusClass[status]}`}>
      <div className="text-sm font-medium text-[#5f786c]">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-foreground">{value}</div>
      {detail ? <div className="mt-2 text-sm text-[#60786c]">{detail}</div> : null}
    </section>
  );
}

