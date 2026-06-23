insert into public.core_empresas (nome, cnpj, slug)
values ('Equipe Norte', null, 'equipe-norte')
on conflict (slug) do nothing;

