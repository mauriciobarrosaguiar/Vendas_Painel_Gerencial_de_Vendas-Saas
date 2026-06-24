create extension if not exists "pgcrypto";

create table if not exists public.core_empresas (
  id uuid primary key default gen_random_uuid(),
  nome text not null,
  cnpj text,
  slug text unique not null,
  ativo boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.core_usuarios (
  id uuid primary key references auth.users(id) on delete cascade,
  empresa_id uuid references public.core_empresas(id) on delete cascade,
  nome text not null,
  email text not null,
  papel text not null check (papel in ('admin_master', 'admin_empresa', 'gestor', 'consultor', 'visualizador')),
  ativo boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.painel_bases (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references public.core_empresas(id) on delete cascade,
  tipo_base text not null check (tipo_base in ('bussola', 'painel', 'produtos_mix', 'acoes', 'mercado_farma', 'bussola_historico')),
  nome_arquivo text not null,
  storage_path text not null,
  linhas integer not null default 0,
  colunas integer not null default 0,
  hash_arquivo text not null,
  ativo boolean not null default true,
  uploaded_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);

create table if not exists public.painel_metas (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references public.core_empresas(id) on delete cascade,
  ano_mes text not null,
  escopo text not null check (escopo in ('gerente_territorial', 'consultor')),
  consultor text,
  ol_sem_combate numeric not null default 0,
  ol_prioritarios numeric not null default 0,
  ol_lancamentos numeric not null default 0,
  clientes_positivados numeric not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.painel_sips (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references public.core_empresas(id) on delete cascade,
  nome text not null,
  slug text not null,
  redes jsonb not null default '[]'::jsonb,
  cnpjs jsonb not null default '[]'::jsonb,
  meta_mes numeric not null default 0,
  pagamento_percentual numeric not null default 80,
  ativo boolean not null default true,
  created_at timestamptz not null default now(),
  unique (empresa_id, slug)
);

create table if not exists public.painel_sip_recados (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references public.core_empresas(id) on delete cascade,
  sip_id uuid not null references public.painel_sips(id) on delete cascade,
  titulo text not null,
  comentario text,
  status text not null default 'Pendente',
  imagem_path text,
  created_at timestamptz not null default now()
);

create table if not exists public.painel_acoes_promocionais (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references public.core_empresas(id) on delete cascade,
  campanha text,
  produto text,
  ean text,
  tipo_mix text,
  distribuidora text,
  desconto numeric not null default 0,
  data_inicio date,
  data_fim date,
  consultor text,
  observacao text,
  status text,
  created_at timestamptz not null default now()
);

create table if not exists public.painel_foco_semanal (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references public.core_empresas(id) on delete cascade,
  nome text not null,
  data_inicio date,
  data_fim date,
  eans jsonb not null default '[]'::jsonb,
  metas_produtos jsonb not null default '[]'::jsonb,
  metas_consultores jsonb not null default '{}'::jsonb,
  configuracao jsonb not null default '{}'::jsonb,
  ativo boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.painel_ajustes_vendedores (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references public.core_empresas(id) on delete cascade,
  setor_rep text,
  nome_original text,
  nome_ajustado text,
  ativo boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.painel_extracoes (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid not null references public.core_empresas(id) on delete cascade,
  tipo text not null,
  status text not null,
  parametros jsonb not null default '{}'::jsonb,
  resultado jsonb not null default '{}'::jsonb,
  erro text,
  github_run_id text,
  created_at timestamptz not null default now(),
  finished_at timestamptz
);

create table if not exists public.painel_logs (
  id uuid primary key default gen_random_uuid(),
  empresa_id uuid references public.core_empresas(id) on delete cascade,
  usuario_id uuid references auth.users(id) on delete set null,
  acao text not null,
  detalhes jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_core_usuarios_empresa on public.core_usuarios (empresa_id);
create index if not exists idx_painel_bases_empresa_tipo on public.painel_bases (empresa_id, tipo_base, ativo);
create index if not exists idx_painel_metas_empresa_mes on public.painel_metas (empresa_id, ano_mes);
create index if not exists idx_painel_sips_empresa_slug on public.painel_sips (empresa_id, slug);

