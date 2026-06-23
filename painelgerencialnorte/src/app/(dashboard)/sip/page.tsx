import { SectionPage } from "@/components/dashboard/SectionPage";

export default function SipPage() {
  return (
    <SectionPage
      title="SIP"
      description="Cadastro, meta mensal, percentual de pagamento, recados, pedidos, notas e link publico por slug."
      columns={["SIP", "CNPJs", "Meta", "Faturado", "Falta regra", "Link publico"]}
    />
  );
}

