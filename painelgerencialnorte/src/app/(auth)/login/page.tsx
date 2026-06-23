import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-background px-4">
      <section className="w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-sm">
        <div className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">painelgerencialnorte</div>
        <h1 className="mt-2 text-2xl font-semibold text-foreground">Entrar no painel</h1>
        <p className="mt-2 text-sm text-[#60786c]">
          Login SaaS com Supabase Auth. Nenhuma tela interna deve abrir sem sessao, exceto o link publico da SIP.
        </p>
        <LoginForm />
      </section>
    </main>
  );
}

