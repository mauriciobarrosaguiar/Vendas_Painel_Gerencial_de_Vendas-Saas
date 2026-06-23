import { SectionPage } from "@/components/dashboard/SectionPage";

export default function FocoSemanalPage() {
  return (
    <SectionPage
      title="Foco Semanal"
      description="Produtos por EAN, metas por produto e consultor, CNPJs positivados e resultado por molecula."
      columns={["Acao", "Periodo", "Produtos", "Quantidade", "CNPJs", "Status"]}
    />
  );
}

