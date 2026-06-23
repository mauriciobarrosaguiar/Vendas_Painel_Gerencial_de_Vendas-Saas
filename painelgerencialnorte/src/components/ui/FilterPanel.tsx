export function FilterPanel() {
  return (
    <section className="grid gap-3 rounded-lg border border-border bg-surface p-4 md:grid-cols-4">
      <label className="text-sm">
        <span className="mb-1 block font-medium text-[#5f786c]">Periodo</span>
        <input className="focus-ring w-full rounded-md border border-border px-3 py-2" type="month" />
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-[#5f786c]">Consultor</span>
        <select className="focus-ring w-full rounded-md border border-border px-3 py-2">
          <option>Todos</option>
        </select>
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-[#5f786c]">UF</span>
        <select className="focus-ring w-full rounded-md border border-border px-3 py-2">
          <option>Todas</option>
        </select>
      </label>
      <label className="text-sm">
        <span className="mb-1 block font-medium text-[#5f786c]">Status</span>
        <select className="focus-ring w-full rounded-md border border-border px-3 py-2">
          <option>Apenas faturados</option>
        </select>
      </label>
    </section>
  );
}

