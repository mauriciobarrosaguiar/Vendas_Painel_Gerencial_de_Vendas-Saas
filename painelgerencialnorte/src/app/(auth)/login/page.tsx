export default function LoginPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-background px-4">
      <section className="w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-sm">
        <div className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">painelgerencialnorte</div>
        <h1 className="mt-2 text-2xl font-semibold text-foreground">Entrar no painel</h1>
        <p className="mt-2 text-sm text-[#60786c]">
          Login SaaS com Supabase Auth. Nenhuma tela interna deve abrir sem sessao, exceto o link publico da SIP.
        </p>
        <form className="mt-6 space-y-4">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-[#5f786c]">Email</span>
            <input className="focus-ring w-full rounded-md border border-border px-3 py-2" type="email" placeholder="usuario@empresa.com" />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-[#5f786c]">Senha</span>
            <input className="focus-ring w-full rounded-md border border-border px-3 py-2" type="password" placeholder="Sua senha" />
          </label>
          <button className="focus-ring w-full rounded-md bg-primary px-4 py-2 font-semibold text-white hover:bg-[#0f5838]" type="button">
            Entrar
          </button>
        </form>
      </section>
    </main>
  );
}

