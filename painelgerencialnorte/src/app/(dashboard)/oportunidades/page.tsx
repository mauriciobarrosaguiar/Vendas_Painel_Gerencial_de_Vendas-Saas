import { SectionPage } from "@/components/dashboard/SectionPage";

export default function OportunidadesPage() {
  return (
    <SectionPage
      title="Oportunidades"
      description="Clientes sem compra, sem prioritarios, sem lancamentos e sugestoes com Mercado Farma quando disponivel."
      columns={["Prioridade", "Cliente", "CNPJ", "Motivo", "Acao sugerida", "Consultor"]}
    />
  );
}

