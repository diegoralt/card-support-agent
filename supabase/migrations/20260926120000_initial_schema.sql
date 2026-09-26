-- Esquema inicial de card-support-agent (spec v0.4).
--
-- Seguridad: la app se conecta solo por la cadena de conexión de Postgres (rol
-- postgres, desde los secrets de Streamlit); no usa la API REST. Por eso todas las
-- tablas tienen RLS sin políticas y se revocan los grants a anon/authenticated: el
-- repo es público y la URL del proyecto no debe dar acceso a nada.

create extension if not exists vector with schema extensions;

create table public.customers (
  id integer primary key,
  name text not null,
  email text not null unique,
  kyc_status text not null check (kyc_status in ('approved', 'pending'))
);

-- status no cambia con el bloqueo de la demo: el bloqueo vive en la sesión (spec §2).
create table public.cards (
  id integer primary key,
  customer_id integer not null references public.customers (id),
  last4 char(4) not null check (last4 ~ '^[0-9]{4}$'),
  status text not null default 'active' check (status in ('active', 'blocked')),
  credit_limit numeric(12, 2) not null check (credit_limit > 0)
);

create table public.transactions (
  id bigint generated always as identity primary key,
  card_id integer not null references public.cards (id),
  date date not null,
  merchant text not null,
  amount numeric(12, 2) not null,
  type text not null check (type in ('purchase', 'payment'))
);
create index transactions_card_date_idx on public.transactions (card_id, date);

create table public.policy_chunks (
  id bigint generated always as identity primary key,
  file text not null,
  section text not null,
  content text not null,
  embedding extensions.vector(1536) not null,
  unique (file, section)
);
create index policy_chunks_embedding_idx on public.policy_chunks
  using hnsw (embedding extensions.vector_cosine_ops);

create table public.tickets (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  session_id text not null,
  customer_id integer not null references public.customers (id),
  reason text not null,
  origin text not null check (origin in ('demo', 'eval')),
  status text not null default 'open' check (status in ('open', 'closed'))
);

-- Sin texto de mensajes: solo métricas (spec §2, datos de visitantes de la demo).
create table public.llm_calls (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  session_id text not null,
  origin text not null check (origin in ('demo', 'eval', 'ingest')),
  kind text not null check (kind in ('chat', 'embedding', 'judge')),
  model text not null,
  prompt_tokens integer not null default 0,
  completion_tokens integer not null default 0,
  cached_tokens integer not null default 0,
  cost_usd numeric(12, 8) not null default 0,
  latency_ms integer not null,
  tools jsonb not null default '[]',  -- [{name, args, customer_id}]
  chunks jsonb not null default '[]'  -- [{id, similarity}]
);
create index llm_calls_session_idx on public.llm_calls (session_id);

alter table public.customers enable row level security;
alter table public.cards enable row level security;
alter table public.transactions enable row level security;
alter table public.policy_chunks enable row level security;
alter table public.tickets enable row level security;
alter table public.llm_calls enable row level security;

revoke all on public.customers, public.cards, public.transactions,
  public.policy_chunks, public.tickets, public.llm_calls
  from anon, authenticated;
