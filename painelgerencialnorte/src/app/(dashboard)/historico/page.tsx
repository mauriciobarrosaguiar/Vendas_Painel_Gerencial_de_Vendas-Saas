import { SectionPage } from "@/components/dashboard/SectionPage";

export default function HistoricoPage() {
  return (
    <SectionPage
      title="Historico"
      description="Bussola historico, metas fechadas, resumo por GD, por vendedor e produtos vendidos."
      columns={["Mes", "Escopo", "OL sem combate", "Meta OL", "Atingimento", "Clientes"]}
    />
  );
}

