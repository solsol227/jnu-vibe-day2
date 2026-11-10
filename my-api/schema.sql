-- Supabase 대시보드 > SQL Editor 에서 한 번 실행하세요.
create table if not exists public.places (
  id bigint generated always as identity primary key,
  name text not null,
  description text not null default '',
  created_at timestamptz not null default now()
);

-- 서버(secret key)만 접근하므로 RLS 켜고 정책은 만들지 않음 (secret key는 RLS를 우회)
alter table public.places enable row level security;

insert into public.places (name, description) values
  ('한라산', '대한민국 최고봉'),
  ('성산일출봉', '유네스코 세계자연유산');
