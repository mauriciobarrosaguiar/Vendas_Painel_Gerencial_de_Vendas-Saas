# painelgerencialnorte

Frontend Next.js App Router do Painel Gerencial Norte.

Este app e publicado pela raiz do repositorio via Vercel Services:

- frontend: `painelgerencialnorte/` em `/`
- backend: `backend/main.py` em `/api`

Rodar localmente:

```bash
npm install
npm run dev
```

O script local usa Webpack (`next dev --webpack`) porque Turbopack exige bindings nativos do SWC.

Para consumir a API FastAPI local pelo proxy `/api`, configure `BACKEND_URL=http://127.0.0.1:8000`.
