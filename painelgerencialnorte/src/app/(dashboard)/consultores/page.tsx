import { SectionPage } from "@/components/dashboard/SectionPage";

export default function ConsultoresPage() {
  return (
    <SectionPage
      title="Consultores"
      description="Cards por consultor, metas individuais, status operacional, ranking e carteira exportavel."
      columns={["Consultor", "OL sem combate", "Prioritarios", "Lancamentos", "Clientes com venda", "Status"]}
    />
  );
}

