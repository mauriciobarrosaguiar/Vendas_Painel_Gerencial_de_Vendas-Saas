import { SectionPage } from "@/components/dashboard/SectionPage";

export default function ConfiguracoesPage() {
  return (
    <SectionPage
      title="Configuracoes"
      description="Empresa, usuarios, papeis, metas, ajustes de vendedor, credenciais de integracao e logs."
      columns={["Area", "Permissao", "Ultima alteracao", "Status"]}
    />
  );
}

