# Deploy Painel Gerencial Norte SaaS

## Fluxo Real

1. Crie o projeto no Supabase.
2. Rode `supabase/schema.sql`.
3. Rode `supabase/policies.sql`.
4. Rode `supabase/seed.sql`.
5. Crie o bucket privado `painel-bases` no Supabase Storage ou deixe o backend criar no primeiro upload usando `SUPABASE_SERVICE_ROLE_KEY`.
6. Configure as variaveis no Vercel.
7. Faca deploy da branch `main`.
8. Abra `/dashboard` sem login.
9. Abra `/importacao` sem login.
10. Baixe os modelos em `/templates` ou nos cards de `/importacao`.
11. Importe Painel clientes.
12. Importe Produtos / Mix.
13. Importe Bussola.
14. Volte ao Dashboard e confirme os indicadores calculados.
15. Nunca commite planilhas reais com CNPJ/clientes no GitHub.

## Variaveis Vercel

```text
PUBLIC_PANEL_MODE=true
PUBLIC_EMPRESA_SLUG=equipe-norte
PUBLIC_SHOW_AUTOMATIONS=false
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
NEXT_PUBLIC_BACKEND_URL=/api
PERSISTENCE_KEY=
GITHUB_REPO=
GITHUB_TOKEN=
GITHUB_STORAGE_BRANCH=
GITHUB_STORE_DIR=
NODE_OPTIONS=--use-system-ca
```

O painel de usuario final e publico. Nao e necessario criar usuario no Supabase Auth para acessar as telas.

## Supabase Storage

O upload manual salva os arquivos no bucket `painel-bases`, preferencialmente privado, no caminho:

```text
<empresa_id>/<tipo_base>/<ano_mes>/<nome_arquivo>
```

Cada importacao cria um registro em `public.painel_bases`. Quando uma nova base do mesmo `tipo_base` e `empresa_id` entra, a anterior fica `ativo=false` e a nova fica `ativo=true`, mantendo historico.

## Validacao

1. `GET /api/health` deve retornar `{"ok": true}`.
2. `GET /api/templates` deve listar os modelos.
3. `GET /api/dashboard` sem base deve retornar estado vazio controlado.
4. `POST /api/importacao` deve aceitar upload sem `Authorization`.
5. `GET /api/dashboard` apos Painel clientes + Bussola deve calcular com dados reais.

## Modelos

Os modelos ficam em `painelgerencialnorte/public/modelos/` e sao arquivos `.xlsx` reais, com aba principal, exemplos ficticios e aba `Instruções`.

## Automacoes

As automacoes de Bussola e Mercado Farma ficam ocultas por padrao com:

```text
PUBLIC_SHOW_AUTOMATIONS=false
```

Se forem habilitadas, configure `GITHUB_REPO`, `GITHUB_TOKEN`, `PERSISTENCE_KEY` e os secrets necessarios nos workflows. As credenciais salvas pelo painel ficam criptografadas com `PERSISTENCE_KEY`.

## Seguranca

- Nao commite `.env.production.local`, `.vercel/`, chaves do Supabase, GitHub Token ou planilhas reais.
- `SUPABASE_SERVICE_ROLE_KEY` deve existir apenas no backend/Vercel.
- Dados reais entram pelo navegador e sao persistidos no Supabase Storage e em `public.painel_bases`.
- Se `npm install` falhar por certificado no Windows, use `NODE_OPTIONS=--use-system-ca`; nao desabilite validacao TLS.
