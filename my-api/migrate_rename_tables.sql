-- 기존 테이블 이름에 jnu_vc2_ 접두사를 붙입니다. (데이터/FK/RLS 설정은 그대로 유지)
-- Supabase 대시보드 > SQL Editor 에서 한 번만 실행하세요.
alter table public.places     rename to jnu_vc2_places;
alter table public.products   rename to jnu_vc2_products;
alter table public.cart_items rename to jnu_vc2_cart_items;
