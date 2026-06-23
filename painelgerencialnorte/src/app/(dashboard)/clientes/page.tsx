import { SectionPage } from "@/components/dashboard/SectionPage";

export default function ClientesPage() {
  return (
    <SectionPage
      title="Clientes"
      description="Busca por cliente, CNPJ, cidade, consultor e rede, com contatos e status comercial preservados."
      columns={["Cliente", "CNPJ", "Consultor", "Rede", "OL sem combate", "Status comercial"]}
    />
  );
}

