export default async function SipPublicoPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  return (
    <main className="min-h-screen bg-background px-4 py-6">
      <section className="mx-auto max-w-5xl space-y-5">
        <div className="rounded-lg border border-border bg-surface p-5">
          <div className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">Acesso publico SIP</div>
          <h1 className="mt-2 text-2xl font-semibold text-foreground">{slug}</h1>
          <p className="mt-2 text-sm text-[#60786c]">
            Esta rota sera alimentada por /api/sip-publico/[slug] com dados limitados da SIP, sem expor outras empresas ou grupos.
          </p>
        </div>
      </section>
    </main>
  );
}

