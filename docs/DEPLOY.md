# Deploy Painel Gerencial Norte SaaS

## Supabase

1. Crie o projeto no Supabase.
2. Rode `supabase/schema.sql`.
3. Rode `supabase/policies.sql`.
4. Rode `supabase/seed.sql`.
5. Rode `supabase/storage.sql`.
6. Crie o usuario em Authentication.
7. Vincule o usuario em `public.core_usuarios` como `admin_master`.
8. Em Authentication URL Configuration, configure:

Site URL:

```text
https://painelgerencialnorte.vercel.app
```

Redirect URLs:

```text
https://painelgerencialnorte.vercel.app/**
http://localhost:3000/**
```

## Vercel

1. Importe o repositorio `mauriciobarrosaguiar/Vendas_Painel_Gerencial_de_Vendas-Saas`.
2. Use root directory `./`.
3. Use Application Preset `Services`.
4. Configure as variaveis de ambiente:

```text
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
NEXT_PUBLIC_BACKEND_URL=/api
BACKEND_URL=
PERSISTENCE_KEY=
GITHUB_REPO=
GITHUB_TOKEN=
GITHUB_STORAGE_BRANCH=
GITHUB_STORE_DIR=
MERCADOFARMA_USUARIO=
MERCADOFARMA_SENHA=
NODE_OPTIONS=--use-system-ca
```

5. Faça deploy da branch `main`.

## Validacao

1. Acesse `/api/health`; a resposta deve ser `{"ok": true}`.
2. Acesse `/login` e entre com o usuario criado no Supabase Auth.
3. Abra `/dashboard`; sem bases, deve mostrar `Nenhuma base importada ainda`.
4. Abra `/importacao` e envie as bases.
5. Confirme que os arquivos foram salvos no bucket privado `painel-bases`.
6. Confirme que `public.painel_bases` recebeu o registro do upload.
7. Volte ao dashboard e confira os indicadores calculados pelo backend Python.

## Regra de historico de bases

A importacao preserva todos os uploads no Storage e em `public.painel_bases`.
Quando uma nova base do mesmo `tipo_base` e `empresa_id` e importada com sucesso, o backend marca as bases anteriores desse mesmo tipo como `ativo = false` e usa a base ativa mais recente no dashboard.

## Seguranca

- `SUPABASE_SERVICE_ROLE_KEY` existe apenas no backend/Vercel.
- O frontend usa somente `NEXT_PUBLIC_SUPABASE_URL` e `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- O backend valida o bearer token do Supabase Auth antes de aceitar importacao.
- Quando o backend usa service role, ele aplica filtro manual por `empresa_id`.
