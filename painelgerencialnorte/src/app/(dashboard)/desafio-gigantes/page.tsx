import { SectionPage } from "@/components/dashboard/SectionPage";

export default function DesafioGigantesPage() {
  return (
    <SectionPage
      title="Desafio de Gigantes"
      description="Tela mantida para a campanha, pronta para reaproveitar as regras de src/desafio.py no core."
      columns={["SKU", "Produto", "Meta positivacao", "Meta giro", "Pontos", "Status"]}
    />
  );
}

