import { baseTemplates } from "@/lib/baseTemplates";

export function TemplatesTable() {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-muted text-xs uppercase tracking-[0.08em] text-[#5f786c]">
            <tr>
              <th className="px-4 py-3 font-semibold">Modelo</th>
              <th className="px-4 py-3 font-semibold">Arquivo</th>
              <th className="px-4 py-3 font-semibold">Aba</th>
              <th className="px-4 py-3 font-semibold">Colunas obrigatorias</th>
              <th className="px-4 py-3 font-semibold">Download</th>
            </tr>
          </thead>
          <tbody>
            {baseTemplates.map((template) => (
              <tr key={template.typeBase} className="border-t border-border">
                <td className="px-4 py-3 font-semibold text-[#183b2d]">{template.title}</td>
                <td className="px-4 py-3 text-[#183b2d]">{template.arquivo}</td>
                <td className="px-4 py-3 text-[#183b2d]">{template.aba}</td>
                <td className="px-4 py-3 text-[#183b2d]">{template.colunas.join(", ")}</td>
                <td className="px-4 py-3">
                  <a
                    className="focus-ring inline-flex rounded-md bg-primary px-3 py-2 text-xs font-semibold text-white hover:bg-[#0f5838]"
                    href={template.modelUrl}
                    download
                  >
                    Baixar modelo
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
