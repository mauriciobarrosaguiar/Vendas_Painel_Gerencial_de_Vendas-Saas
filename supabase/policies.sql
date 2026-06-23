alter table public.core_empresas enable row level security;
alter table public.core_usuarios enable row level security;
alter table public.painel_bases enable row level security;
alter table public.painel_metas enable row level security;
alter table public.painel_sips enable row level security;
alter table public.painel_sip_recados enable row level security;
alter table public.painel_acoes_promocionais enable row level security;
alter table public.painel_foco_semanal enable row level security;
alter table public.painel_ajustes_vendedores enable row level security;
alter table public.painel_extracoes enable row level security;
alter table public.painel_logs enable row level security;

create or replace function public.usuario_empresa_id()
returns uuid
language sql
security definer
set search_path = public
as $$
  select empresa_id from public.core_usuarios where id = auth.uid() and ativo = true limit 1
$$;

create or replace function public.usuario_papel()
returns text
language sql
security definer
set search_path = public
as $$
  select papel from public.core_usuarios where id = auth.uid() and ativo = true limit 1
$$;

create or replace function public.is_admin_master()
returns boolean
language sql
security definer
set search_path = public
as $$
  select coalesce(public.usuario_papel() = 'admin_master', false)
$$;

drop policy if exists "empresas por usuario" on public.core_empresas;
drop policy if exists "usuarios da propria empresa" on public.core_usuarios;
drop policy if exists "usuarios gerenciaveis por admins" on public.core_usuarios;
drop policy if exists "bases por empresa" on public.painel_bases;
drop policy if exists "metas por empresa" on public.painel_metas;
drop policy if exists "sips por empresa" on public.painel_sips;
drop policy if exists "recados sip por empresa" on public.painel_sip_recados;
drop policy if exists "acoes por empresa" on public.painel_acoes_promocionais;
drop policy if exists "foco semanal por empresa" on public.painel_foco_semanal;
drop policy if exists "ajustes vendedores por empresa" on public.painel_ajustes_vendedores;
drop policy if exists "extracoes por empresa" on public.painel_extracoes;
drop policy if exists "logs por empresa" on public.painel_logs;

create policy "empresas por usuario" on public.core_empresas
for select using (public.is_admin_master() or id = public.usuario_empresa_id());

create policy "usuarios da propria empresa" on public.core_usuarios
for select using (public.is_admin_master() or empresa_id = public.usuario_empresa_id());

create policy "usuarios gerenciaveis por admins" on public.core_usuarios
for all using (public.is_admin_master() or (empresa_id = public.usuario_empresa_id() and public.usuario_papel() = 'admin_empresa'))
with check (public.is_admin_master() or (empresa_id = public.usuario_empresa_id() and public.usuario_papel() = 'admin_empresa'));

create policy "bases por empresa" on public.painel_bases
for all using (public.is_admin_master() or empresa_id = public.usuario_empresa_id())
with check (public.is_admin_master() or empresa_id = public.usuario_empresa_id());

create policy "metas por empresa" on public.painel_metas
for all using (public.is_admin_master() or empresa_id = public.usuario_empresa_id())
with check (public.is_admin_master() or empresa_id = public.usuario_empresa_id());

create policy "sips por empresa" on public.painel_sips
for all using (public.is_admin_master() or empresa_id = public.usuario_empresa_id())
with check (public.is_admin_master() or empresa_id = public.usuario_empresa_id());

create policy "recados sip por empresa" on public.painel_sip_recados
for all using (public.is_admin_master() or empresa_id = public.usuario_empresa_id())
with check (public.is_admin_master() or empresa_id = public.usuario_empresa_id());

create policy "acoes por empresa" on public.painel_acoes_promocionais
for all using (public.is_admin_master() or empresa_id = public.usuario_empresa_id())
with check (public.is_admin_master() or empresa_id = public.usuario_empresa_id());

create policy "foco semanal por empresa" on public.painel_foco_semanal
for all using (public.is_admin_master() or empresa_id = public.usuario_empresa_id())
with check (public.is_admin_master() or empresa_id = public.usuario_empresa_id());

create policy "ajustes vendedores por empresa" on public.painel_ajustes_vendedores
for all using (public.is_admin_master() or empresa_id = public.usuario_empresa_id())
with check (public.is_admin_master() or empresa_id = public.usuario_empresa_id());

create policy "extracoes por empresa" on public.painel_extracoes
for all using (public.is_admin_master() or empresa_id = public.usuario_empresa_id())
with check (public.is_admin_master() or empresa_id = public.usuario_empresa_id());

create policy "logs por empresa" on public.painel_logs
for all using (public.is_admin_master() or empresa_id = public.usuario_empresa_id())
with check (public.is_admin_master() or empresa_id = public.usuario_empresa_id());

-- A rota publica /sip/[slug] deve usar endpoint controlado, nao acesso direto anonimo amplo.
