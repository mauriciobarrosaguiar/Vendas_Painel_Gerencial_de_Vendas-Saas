import Link from "next/link";
import { navigationGroups } from "@/lib/navigation";

export function AppSidebar() {
  return (
    <aside className="hidden w-72 shrink-0 border-r border-border bg-[#eef5ea] lg:flex lg:flex-col">
      <div className="border-b border-border px-5 py-5">
        <div className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">Equipe Norte</div>
        <div className="mt-1 text-xl font-semibold text-foreground">Painel Gerencial</div>
      </div>
      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
        {navigationGroups.map((group) => (
          <div key={group.label}>
            <div className="px-3 text-xs font-semibold uppercase tracking-[0.14em] text-[#5f786c]">{group.label}</div>
            <div className="mt-2 space-y-1">
              {group.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="block rounded-md px-3 py-2 text-sm font-medium text-[#183b2d] transition hover:bg-white hover:text-primary"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  );
}

