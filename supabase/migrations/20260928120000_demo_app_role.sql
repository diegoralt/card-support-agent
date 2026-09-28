-- Rol de mínimo privilegio para la demo pública (Streamlit).
-- Antes la app entraba como `postgres`: dueño de todo y con bypass de RLS. Si se filtraran
-- los secrets de Streamlit, daban control total de la BD. Con este rol solo se puede leer
-- lo que la demo muestra e insertar tickets y trazas; nada de update, delete ni DDL.
-- La contraseña NO va aquí (repo público): se fija fuera del repo con
--   alter role demo_app password '...';

create role demo_app login noinherit;

grant usage on schema public to demo_app;
-- La búsqueda vectorial usa extensions.<=> y extensions.vector.
grant usage on schema extensions to demo_app;

grant select on public.customers, public.cards, public.transactions, public.policy_chunks
  to demo_app;
-- select en tickets y llm_calls: la UI lee los folios de la sesión y el gasto del día,
-- y `insert ... returning id` requiere select sobre la columna devuelta.
grant select, insert on public.tickets, public.llm_calls to demo_app;
grant usage on sequence public.tickets_id_seq, public.llm_calls_id_seq to demo_app;

-- RLS sigue activo y sin políticas para anon/authenticated: solo demo_app pasa, y solo
-- con la operación que se le otorgó arriba.
create policy demo_app_read on public.customers for select to demo_app using (true);
create policy demo_app_read on public.cards for select to demo_app using (true);
create policy demo_app_read on public.transactions for select to demo_app using (true);
create policy demo_app_read on public.policy_chunks for select to demo_app using (true);
create policy demo_app_read on public.tickets for select to demo_app using (true);
create policy demo_app_insert on public.tickets for insert to demo_app with check (true);
create policy demo_app_read on public.llm_calls for select to demo_app using (true);
create policy demo_app_insert on public.llm_calls for insert to demo_app with check (true);
