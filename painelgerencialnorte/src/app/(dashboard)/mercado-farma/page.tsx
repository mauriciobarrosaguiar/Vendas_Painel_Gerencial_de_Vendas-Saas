import { SectionPage } from "@/components/dashboard/SectionPage";

export default function MercadoFarmaPage() {
  return (
    <SectionPage
      title="Mercado Farma / UF"
      description="Melhores precos por EAN, estoque, distribuidora, desconto adicional, status de extracao e Excel por UF."
      columns={["UF", "EAN", "Produto", "Distribuidora", "Estoque", "Preco sem imposto"]}
    />
  );
}

