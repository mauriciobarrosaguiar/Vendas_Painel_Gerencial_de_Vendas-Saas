-- Idempotent migration for the public SaaS import flow.
-- Produtos / Mix is now the only product list used by dashboard mix
-- classification and Mercado Farma EAN extraction.

alter table if exists public.painel_bases
  alter column uploaded_by drop not null;

do $$
declare
  constraint_name text;
begin
  if to_regclass('public.painel_bases') is null then
    return;
  end if;

  for constraint_name in
    select conname
    from pg_constraint
    where conrelid = 'public.painel_bases'::regclass
      and contype = 'c'
      and pg_get_constraintdef(oid) like '%tipo_base%'
  loop
    execute format('alter table public.painel_bases drop constraint if exists %I', constraint_name);
  end loop;
end $$;

do $$
begin
  if to_regclass('public.painel_bases') is null then
    return;
  end if;

  update public.painel_bases
     set tipo_base = 'produtos_mix'
   where tipo_base = 'produtos_mercado_farma';

  alter table public.painel_bases
    add constraint painel_bases_tipo_base_check
    check (tipo_base in ('bussola', 'painel', 'produtos_mix', 'acoes', 'mercado_farma', 'bussola_historico'));

  create index if not exists idx_painel_bases_empresa_tipo_ativo_created
    on public.painel_bases (empresa_id, tipo_base, ativo, created_at desc);
end $$;
