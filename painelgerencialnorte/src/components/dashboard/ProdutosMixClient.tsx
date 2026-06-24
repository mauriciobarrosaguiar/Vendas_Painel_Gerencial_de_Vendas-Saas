"use client";

import { useEffect, useState } from "react";
import { DataTable } from "@/components/ui/DataTable";
import { ExportButton } from "@/components/ui/ExportButton";
import { FilterPanel } from "@/components/ui/FilterPanel";
import { apiPath } from "@/lib/api";

type ProdutosMixPayload = {
  ok?: boolean;
  available?: boolean;
  message?: string;
  total_produtos?: number;
  produtos?: Array<Record<string, string | number | null | undefined>>;
};

const columns = ["EAN", "Produto", "Tipo mix", "OL sem combate", "Quantidade", "Clientes"];

export function ProdutosMixClient() {
  const [payload, setPayload] = useState<ProdutosMixPayload>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    fetch(apiPath("/produtos-mix"), { cache: "no-store" })
      .then((response) => response.json())
      .then((data: ProdutosMixPayload) => {
        if (active) {
          setPayload(data);
        }
      })
      .catch(() => {
        if (active) {
          setPayload({ available: false, message: "Falha ao carregar Produtos / Mix." });
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const rows = payload.produtos ?? [];
  const message = loading ? "Carregando Produtos / Mix..." : payload.message || "Nenhuma base Produtos / Mix importada ainda.";

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Produtos / Mix</h2>
          <p className="mt-1 max-w-3xl text-sm text-[#60786c]">
            Auditoria do template, vendidos fora do mix, filtros por PRIORITARIO, LANCAMENTO, LINHA e COMBATE.
          </p>
        </div>
        <ExportButton label="Exportar Excel" />
      </div>
      <FilterPanel />
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-sm text-[#60786c]">{message}</p>
        {payload.available ? (
          <p className="mt-1 text-sm font-medium text-primary">{payload.total_produtos ?? rows.length} produto(s) na base ativa.</p>
        ) : null}
      </div>
      <DataTable columns={columns} rows={rows} emptyText={message} />
    </div>
  );
}
