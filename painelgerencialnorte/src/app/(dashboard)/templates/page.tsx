import { TemplatesTable } from "@/components/dashboard/TemplatesTable";

export default function TemplatesPage() {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">Templates de Bases</h2>
        <p className="mt-1 max-w-3xl text-sm text-[#60786c]">
          Baixe os modelos padrao antes de importar. Use dados reais somente pelo painel publicado; nao envie planilhas com clientes/CNPJ para o GitHub.
        </p>
      </div>
      <TemplatesTable />
    </div>
  );
}
