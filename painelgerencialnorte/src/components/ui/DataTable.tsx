type DataTableProps = {
  columns: string[];
  rows?: Array<Record<string, string | number | null | undefined>>;
  emptyText?: string;
};

function getRowKey(row: Record<string, string | number | null | undefined>, columns: string[]): string {
  const explicitKey = row.id ?? row.ID ?? row.codigo ?? row.Codigo ?? row.CNPJ ?? row.EAN;
  if (explicitKey) {
    return String(explicitKey);
  }
  return columns.map((column) => `${column}:${row[column] ?? ""}`).join("|");
}

export function DataTable({ columns, rows = [], emptyText = "Sem dados para exibir." }: DataTableProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-muted text-xs uppercase tracking-[0.08em] text-[#5f786c]">
            <tr>
              {columns.map((column) => (
                <th key={column} className="px-4 py-3 font-semibold">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((row) => (
                <tr key={getRowKey(row, columns)} className="border-t border-border">
                  {columns.map((column) => (
                    <td key={column} className="px-4 py-3 text-[#183b2d]">
                      {row[column] ?? "-"}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td className="px-4 py-8 text-center text-[#60786c]" colSpan={columns.length}>
                  {emptyText}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
