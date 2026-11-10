-- Supabase 대시보드 > SQL Editor 에서 실행하세요. (여러 번 실행해도 안전)

-- 1) 상품
create table if not exists public.products (
  id bigint generated always as identity primary key,
  name text not null,
  description text not null default '',
  price integer not null check (price >= 0),   -- 원 단위
  emoji text not null default '🍊',
  created_at timestamptz not null default now()
);

-- 2) 장바구니 (로그인 없이 브라우저별 cart_id 로 구분)
create table if not exists public.cart_items (
  id bigint generated always as identity primary key,
  cart_id text not null,
  product_id bigint not null references public.products(id) on delete cascade,
  quantity integer not null check (quantity between 1 and 99),
  created_at timestamptz not null default now(),
  unique (cart_id, product_id)
);

-- 서버(secret key)만 접근: RLS 켜고 정책은 만들지 않음
alter table public.products enable row level security;
alter table public.cart_items enable row level security;

-- 3) 샘플 상품 (비어 있을 때만)
insert into public.products (name, description, price, emoji)
select * from (values
  ('한라봉 3kg',        '새콤달콤 과즙 가득, 제주 대표 감귤',        24000, '🍊'),
  ('천혜향 2kg',        '향이 진하고 껍질이 잘 까지는 프리미엄 감귤', 28000, '🍋'),
  ('감귤 초콜릿',       '선물용으로 인기 만점 제주 기념품',          12000, '🍫'),
  ('오메기떡 10개입',   '쫀득한 제주 전통 떡, 팥고물',              15000, '🍡'),
  ('흑돼지 오겹살 600g','쫄깃하고 고소한 제주 흑돼지',              32000, '🐖'),
  ('은갈치 2마리',      '은빛 제주 갈치, 조림용 손질',              35000, '🐟'),
  ('보리빵 6개입',      '제주 보리로 만든 담백한 빵',                9000, '🍞'),
  ('한라산 소주 굿즈 머그컵','제주 여행 기념 머그컵',                 8000, '☕')
) as v(name, description, price, emoji)
where not exists (select 1 from public.products);
