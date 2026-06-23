import { UploadBaseCard } from "@/components/ui/UploadBaseCard";

const bases = [
  ["Bussola", "bussola.xlsx na aba Pedidos"],
  ["Painel clientes", "PAINEL EQUIPE NORTE.xlsx na aba Planilha1"],
  ["Produtos / Mix", "Template com EAN, produto e tipo_mix"],
  ["Acoes promocionais", "Campanhas, EANs, datas, desconto e status"],
  ["Mercado Farma", "Precos, estoque, UF e distribuidora"],
  ["Produtos Mercado Farma", "Lista de EANs para extracao"],
  ["Historico Bussola", "bussola_historico.xlsx na aba Pedidos"],
];

export default function ImportacaoPage() {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">Importacao / Bases</h2>
        <p className="mt-1 text-sm text-[#60786c]">
          Uploads vao para Supabase Storage, com validacao Python, backup automatico e bloqueio contra base invalida.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {bases.map(([title, description]) => (
          <UploadBaseCard key={title} title={title} description={description} />
        ))}
      </div>
    </div>
  );
}

