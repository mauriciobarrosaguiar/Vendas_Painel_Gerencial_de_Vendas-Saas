import { DataTable } from "@/components/ui/DataTable";
import { ExportButton } from "@/components/ui/ExportButton";
import { FilterPanel } from "@/components/ui/FilterPanel";

type SectionPageProps = {
  title: string;
  description: string;
  columns?: string[];
};

export function SectionPage({ title, description, columns = ["Item", "Status", "Origem"] }: SectionPageProps) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">{title}</h2>
          <p className="mt-1 max-w-3xl text-sm text-[#60786c]">{description}</p>
        </div>
        <ExportButton label="Exportar Excel" />
      </div>
      <FilterPanel />
      <DataTable columns={columns} emptyText="Nenhuma base importada ainda." />
    </div>
  );
}

