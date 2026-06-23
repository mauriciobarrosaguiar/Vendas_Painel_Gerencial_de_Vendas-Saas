import { SectionPage } from "@/components/dashboard/SectionPage";

export default function ProdutosMixPage() {
  return (
    <SectionPage
      title="Produtos / Mix"
      description="Auditoria do template, vendidos fora do mix, filtros por PRIORITARIO, LANCAMENTO, LINHA e COMBATE."
      columns={["EAN", "Produto", "Tipo mix", "OL sem combate", "Quantidade", "Clientes"]}
    />
  );
}

