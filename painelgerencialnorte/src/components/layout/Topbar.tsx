import Link from "next/link";

export function Topbar() {
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/95 px-4 py-3 backdrop-blur lg:px-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">painelgerencialnorte</div>
          <h1 className="text-xl font-semibold text-foreground">Equipe Norte</h1>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="rounded-md border border-border bg-surface px-3 py-2 text-[#466155]">Periodo ativo: configuravel</span>
          <Link href="/login" className="rounded-md bg-primary px-4 py-2 font-semibold text-white hover:bg-[#0f5838]">
            Sair
          </Link>
        </div>
      </div>
    </header>
  );
}

