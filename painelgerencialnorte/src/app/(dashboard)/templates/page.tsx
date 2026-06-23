import { SectionPage } from "@/components/dashboard/SectionPage";

export default function TemplatesPage() {
  return (
    <SectionPage
      title="Templates de Bases"
      description="Modelos Excel das bases principais, gerados pela API para preservar nomes de colunas e abas."
      columns={["Modelo", "Arquivo", "Aba", "Colunas obrigatorias", "Download"]}
    />
  );
}

