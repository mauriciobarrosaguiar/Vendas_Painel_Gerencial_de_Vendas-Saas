insert into storage.buckets (id, name, public)
values ('painel-bases', 'painel-bases', false)
on conflict (id) do update set public = excluded.public;

drop policy if exists "painel bases leitura por empresa" on storage.objects;
drop policy if exists "painel bases escrita por empresa" on storage.objects;
drop policy if exists "painel bases atualizacao por empresa" on storage.objects;
drop policy if exists "painel bases remocao por empresa" on storage.objects;

create policy "painel bases leitura por empresa" on storage.objects
for select using (
  bucket_id = 'painel-bases'
  and (
    public.is_admin_master()
    or (storage.foldername(name))[1] = public.usuario_empresa_id()::text
  )
);

create policy "painel bases escrita por empresa" on storage.objects
for insert with check (
  bucket_id = 'painel-bases'
  and (
    public.is_admin_master()
    or (storage.foldername(name))[1] = public.usuario_empresa_id()::text
  )
);

create policy "painel bases atualizacao por empresa" on storage.objects
for update using (
  bucket_id = 'painel-bases'
  and (
    public.is_admin_master()
    or (storage.foldername(name))[1] = public.usuario_empresa_id()::text
  )
)
with check (
  bucket_id = 'painel-bases'
  and (
    public.is_admin_master()
    or (storage.foldername(name))[1] = public.usuario_empresa_id()::text
  )
);

create policy "painel bases remocao por empresa" on storage.objects
for delete using (
  bucket_id = 'painel-bases'
  and (
    public.is_admin_master()
    or (storage.foldername(name))[1] = public.usuario_empresa_id()::text
  )
);

-- O backend usa SUPABASE_SERVICE_ROLE_KEY e tambem cria o bucket se ele ainda nao existir.
-- As policies acima protegem acessos diretos pelo usuario autenticado.
