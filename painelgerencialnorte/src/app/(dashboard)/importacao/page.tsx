import { AutomationImportPanel } from "@/components/ui/AutomationImportPanel";
import { UploadBaseCard } from "@/components/ui/UploadBaseCard";
import { baseTemplates } from "@/lib/baseTemplates";

export default function ImportacaoPage() {
  const showAutomations = process.env.PUBLIC_SHOW_AUTOMATIONS === "true";

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">Importacao / Bases</h2>
        <p className="mt-1 text-sm text-[#60786c]">Envie as bases pelo painel e use os modelos antes de importar.</p>
      </div>
      {showAutomations ? <AutomationImportPanel /> : null}
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {baseTemplates.map((base) => (
          <UploadBaseCard
            key={base.typeBase}
            title={base.title}
            description={base.description}
            typeBase={base.typeBase}
            modelUrl={base.modelUrl}
          />
        ))}
      </div>
    </div>
  );
}
