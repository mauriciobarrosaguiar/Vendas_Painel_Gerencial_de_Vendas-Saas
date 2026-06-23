import { SectionPage } from "@/components/dashboard/SectionPage";

export default function AcoesPromocionaisPage() {
  return (
    <SectionPage
      title="Acoes Promocionais"
      description="Cadastro manual ou planilha, analise antes/durante acao e crescimento percentual."
      columns={["Campanha", "Produto", "EAN", "Antes", "Durante", "Crescimento"]}
    />
  );
}

