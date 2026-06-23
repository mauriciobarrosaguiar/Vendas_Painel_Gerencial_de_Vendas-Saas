# Painel Gerencial Norte

Painel comercial da Equipe Norte. O projeto original em Streamlit continua no repositório como referência funcional, e a migração SaaS para Vercel começou na pasta `painelgerencialnorte/`.

## Estado da migração SaaS

- `backend/core/`: motor Python puro extraído do Streamlit, mantendo as regras de tratamento, indicadores, SIP, projeções, oportunidades, ações e Mercado Farma.
- `tests/`: regressões para proteger os cálculos atuais antes de trocar a interface.
- `painelgerencialnorte/`: frontend Next.js App Router com visual SaaS, Tailwind e estrutura de autenticação/Supabase.
- `backend/main.py`: API FastAPI preparada para Vercel Services em `/api`.
- `supabase/`: schema, políticas RLS e seed inicial para multiempresa.
- `vercel.json`: define dois services, `frontend` em `/` e `backend` em `/api`.

As bases reais não entram no Git. O `.gitignore` mantém fora arquivos locais de Excel, CSV, logs, anexos remotos, credenciais e builds.

## Rodar os testes do core

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Esses testes validam o comportamento do motor atual antes de qualquer troca de tela. Eles devem passar antes de alterar cálculos.

## Rodar o SaaS localmente

Frontend:

```bash
cd painelgerencialnorte
npm install
npm run dev
```

Backend FastAPI:

```bash
python -m pip install -r requirements-dev.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Para o frontend consumir o backend local, use:

```bash
BACKEND_URL=http://127.0.0.1:8000
```

No Vercel Services, a variável `BACKEND_URL` é gerada automaticamente para o service `backend`.

## Publicar na Vercel

1. Crie o projeto a partir da raiz do repositório.
2. Em Project Settings, escolha o Framework Preset `Services`.
3. Configure as variáveis de `.env.example`.
4. Rode as migrações em `supabase/schema.sql`, depois `supabase/policies.sql` e `supabase/seed.sql`.
5. Faça o deploy da branch `saas-vercel`.

## Streamlit legado

O app Streamlit ainda pode ser executado para comparação:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Coloque as bases locais em `data/` quando precisar comparar:

- `bussola.xlsx`
- `PAINEL EQUIPE NORTE.xlsx`
- `template_acoes_promocionais.xlsx`
- `template_produtos_mix.xlsx`
- `sip_grupos.json`
- `metas_comerciais.json`

## Regras preservadas

O core mantém os significados originais de OL sem combate, OL prioritários, OL lançamentos, ticket médio, positivação, clientes sem compra, pedidos sem nota, cancelados, SIP, foco semanal, oportunidades e Mercado Farma.

Antes de mudar qualquer regra, adicione ou ajuste uma regressão em `tests/`.
