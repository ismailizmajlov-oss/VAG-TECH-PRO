
create extension if not exists pgcrypto;
create type public.record_status as enum ('draft','needs_review','verified','superseded','rejected');
create type public.module_code as enum ('MECHANIC','ELECTRICIAN','DIAGNOSTIC','CHIP_TUNING','TRANSMISSION','DIESEL_PRO');
create type public.document_kind as enum ('procedure','specification','wiring_diagram','dtc_reference','diagnostic_test','manual','bulletin');

create table public.profiles (
 id uuid primary key references auth.users(id) on delete cascade,
 display_name text,
 preferred_language text not null default 'ru' check (preferred_language in ('ru','en')),
 created_at timestamptz not null default now()
);
create table public.brands (
 id uuid primary key default gen_random_uuid(), name text not null unique, slug text not null unique,
 is_active boolean not null default true
);
create table public.vehicle_models (
 id uuid primary key default gen_random_uuid(), brand_id uuid not null references public.brands(id),
 name text not null, slug text not null, market text, is_active boolean not null default true,
 unique(brand_id,slug,market)
);
create table public.vehicle_generations (
 id uuid primary key default gen_random_uuid(), model_id uuid not null references public.vehicle_models(id) on delete cascade,
 name text not null, platform_code text, production_start date, production_end date,
 model_year_start smallint, model_year_end smallint, unique(model_id,name)
);
create table public.engines (
 id uuid primary key default gen_random_uuid(), engine_code text not null unique,
 engine_family text, fuel_type text, displacement_cc integer check(displacement_cc is null or displacement_cc>0),
 power_kw numeric(7,2), power_hp numeric(7,2), production_start date, production_end date
);
create table public.transmissions (
 id uuid primary key default gen_random_uuid(), transmission_code text not null unique,
 transmission_type text, gears smallint, drive_type text
);
create table public.ecu_units (
 id uuid primary key default gen_random_uuid(), manufacturer text, ecu_family text,
 hardware_number text, software_number text, ecu_name text,
 unique(hardware_number,software_number)
);
create table public.vehicle_configurations (
 id uuid primary key default gen_random_uuid(),
 generation_id uuid not null references public.vehicle_generations(id),
 engine_id uuid references public.engines(id), transmission_id uuid references public.transmissions(id),
 ecu_id uuid references public.ecu_units(id), market text, production_date date, model_year smallint,
 body_code text, drive_type text, pr_codes text[], vin_pattern text, fitment_notes text,
 source_status public.record_status not null default 'draft', created_at timestamptz not null default now()
);
create table public.modules (
 id uuid primary key default gen_random_uuid(), code public.module_code not null unique,
 title_ru text not null, title_en text not null, description text, is_enabled boolean not null default true,
 sort_order smallint not null default 100
);
create table public.sources (
 id uuid primary key default gen_random_uuid(), publisher text not null, title text not null,
 source_type text, source_url text, document_number text, revision text, published_at date,
 accessed_at timestamptz, license_note text,
 permission_status text not null default 'not_reviewed'
 check(permission_status in ('not_reviewed','licensed','public_domain','user_provided','restricted','permission_required'))
);
create table public.technical_documents (
 id uuid primary key default gen_random_uuid(), module_id uuid references public.modules(id),
 source_id uuid not null references public.sources(id), kind public.document_kind not null,
 title text not null, language text not null default 'en', revision text, document_date date,
 storage_path text, external_reference text, summary text,
 status public.record_status not null default 'draft',
 reviewed_by uuid references public.profiles(id), reviewed_at timestamptz,
 created_by uuid references public.profiles(id), created_at timestamptz not null default now(),
 check(status <> 'verified' or reviewed_at is not null)
);
create table public.document_vehicle_fitment (
 document_id uuid not null references public.technical_documents(id) on delete cascade,
 configuration_id uuid not null references public.vehicle_configurations(id) on delete cascade,
 fitment_note text, primary key(document_id,configuration_id)
);
create table public.procedures (
 id uuid primary key default gen_random_uuid(), document_id uuid not null references public.technical_documents(id) on delete cascade,
 title text not null, objective text, safety_warnings text[], prerequisites text[],
 steps jsonb not null default '[]'::jsonb, status public.record_status not null default 'draft'
);
create table public.procedure_fitment (
 procedure_id uuid not null references public.procedures(id) on delete cascade,
 configuration_id uuid not null references public.vehicle_configurations(id) on delete cascade,
 fitment_note text, primary key(procedure_id,configuration_id)
);
create table public.specifications (
 id uuid primary key default gen_random_uuid(), document_id uuid not null references public.technical_documents(id),
 configuration_id uuid references public.vehicle_configurations(id), system_name text not null,
 component_name text not null, parameter_name text not null, value_text text not null, unit text, conditions text,
 status public.record_status not null default 'draft'
);
create table public.wiring_diagrams (
 id uuid primary key default gen_random_uuid(), document_id uuid not null references public.technical_documents(id),
 configuration_id uuid references public.vehicle_configurations(id), system_name text not null,
 component_name text, connector_id text, pin_number text, wire_color text, wire_function text,
 image_storage_path text, status public.record_status not null default 'draft'
);
create table public.dtc_codes (
 id uuid primary key default gen_random_uuid(), document_id uuid not null references public.technical_documents(id),
 code text not null, system_name text, ecu_family text, description text not null,
 possible_causes text[], diagnostic_notes text, status public.record_status not null default 'draft',
 unique(document_id,code,ecu_family)
);
create table public.diagnostic_tests (
 id uuid primary key default gen_random_uuid(), document_id uuid not null references public.technical_documents(id),
 configuration_id uuid references public.vehicle_configurations(id), title text not null, test_purpose text,
 prerequisites text[], test_steps jsonb not null default '[]'::jsonb,
 expected_results jsonb not null default '[]'::jsonb, status public.record_status not null default 'draft'
);
create table public.subscriptions (
 id uuid primary key default gen_random_uuid(), user_id uuid not null references public.profiles(id) on delete cascade,
 plan_code text not null, status text not null default 'inactive'
 check(status in ('trialing','active','past_due','cancelled','inactive')),
 starts_at timestamptz, ends_at timestamptz, provider text, provider_subscription_id text
);
create table public.query_history (
 id uuid primary key default gen_random_uuid(), user_id uuid not null references public.profiles(id) on delete cascade,
 module_id uuid references public.modules(id), configuration_id uuid references public.vehicle_configurations(id),
 query_text text not null, response_summary text, created_at timestamptz not null default now()
);
create table public.user_bookmarks (
 id uuid primary key default gen_random_uuid(), user_id uuid not null references public.profiles(id) on delete cascade,
 document_id uuid references public.technical_documents(id) on delete cascade,
 procedure_id uuid references public.procedures(id) on delete cascade, label text,
 created_at timestamptz not null default now(), check(document_id is not null or procedure_id is not null)
);

create index vehicle_models_brand_idx on public.vehicle_models(brand_id);
create index vehicle_generations_model_idx on public.vehicle_generations(model_id);
create index vehicle_configurations_generation_idx on public.vehicle_configurations(generation_id);
create index vehicle_configurations_engine_idx on public.vehicle_configurations(engine_id);
create index technical_documents_status_kind_idx on public.technical_documents(status,kind);
create index dtc_codes_code_idx on public.dtc_codes(code);
create index query_history_user_created_idx on public.query_history(user_id,created_at desc);

-- RLS: every exposed public table is protected.
do $$
declare t text;
begin
 foreach t in array array['profiles','brands','vehicle_models','vehicle_generations','engines','transmissions','ecu_units','vehicle_configurations','modules','sources','technical_documents','document_vehicle_fitment','procedures','procedure_fitment','specifications','wiring_diagrams','dtc_codes','diagnostic_tests','subscriptions','query_history','user_bookmarks']
 loop execute format('alter table public.%I enable row level security',t); end loop;
end $$;

create policy "own profile read" on public.profiles for select to authenticated using ((select auth.uid())=id);
create policy "own profile update" on public.profiles for update to authenticated using ((select auth.uid())=id) with check ((select auth.uid())=id);
create policy "active brands read" on public.brands for select to anon,authenticated using (is_active);
create policy "active models read" on public.vehicle_models for select to anon,authenticated using (is_active);
create policy "generations read" on public.vehicle_generations for select to anon,authenticated using (true);
create policy "engines read" on public.engines for select to anon,authenticated using (true);
create policy "transmissions read" on public.transmissions for select to anon,authenticated using (true);
create policy "ecu read" on public.ecu_units for select to anon,authenticated using (true);
create policy "verified configurations read" on public.vehicle_configurations for select to anon,authenticated using (source_status='verified');
create policy "enabled modules read" on public.modules for select to anon,authenticated using (is_enabled);
create policy "verified documents read" on public.technical_documents for select to anon,authenticated using (status='verified');
create policy "verified document fitment read" on public.document_vehicle_fitment for select to anon,authenticated using (exists(select 1 from public.technical_documents d where d.id=document_id and d.status='verified'));
create policy "verified procedures read" on public.procedures for select to anon,authenticated using (status='verified');
create policy "verified procedure fitment read" on public.procedure_fitment for select to anon,authenticated using (exists(select 1 from public.procedures p where p.id=procedure_id and p.status='verified'));
create policy "verified specs read" on public.specifications for select to anon,authenticated using (status='verified');
create policy "verified wiring read" on public.wiring_diagrams for select to anon,authenticated using (status='verified');
create policy "verified DTC read" on public.dtc_codes for select to anon,authenticated using (status='verified');
create policy "verified tests read" on public.diagnostic_tests for select to anon,authenticated using (status='verified');
create policy "own subscriptions read" on public.subscriptions for select to authenticated using ((select auth.uid())=user_id);
create policy "own history read" on public.query_history for select to authenticated using ((select auth.uid())=user_id);
create policy "own history insert" on public.query_history for insert to authenticated with check ((select auth.uid())=user_id);
create policy "own history delete" on public.query_history for delete to authenticated using ((select auth.uid())=user_id);
create policy "own bookmarks manage" on public.user_bookmarks for all to authenticated using ((select auth.uid())=user_id) with check ((select auth.uid())=user_id);

-- Private trigger helper: SECURITY DEFINER is isolated outside exposed public schema and not executable by API roles.
create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
create or replace function private.handle_new_user()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
 insert into public.profiles(id,display_name)
 values(new.id,coalesce(new.raw_user_meta_data->>'full_name',new.raw_user_meta_data->>'name'));
 return new;
end;
$$;
revoke all on function private.handle_new_user() from public, anon, authenticated;
create trigger on_auth_user_created after insert on auth.users for each row execute function private.handle_new_user();

insert into public.modules(code,title_ru,title_en,description,sort_order) values
('MECHANIC','Механика','Mechanic','Ремонт и обслуживание',10),
('ELECTRICIAN','Автоэлектрика','Electrician','Электросхемы, распиновки и проверки',20),
('DIAGNOSTIC','Диагностика','Diagnostic','Коды ошибок, тест-планы и адаптации',30),
('CHIP_TUNING','Чип-тюнинг','Chip Tuning','Калибровки и программное обеспечение',40),
('TRANSMISSION','Трансмиссия','Transmission','Обслуживание и ремонт трансмиссий',50),
('DIESEL_PRO','Дизель','Diesel Pro','Дизельные системы и диагностика',60)
on conflict(code) do nothing;
insert into public.brands(name,slug) values
('Volkswagen','volkswagen'),('Audi','audi'),('Škoda','skoda'),('SEAT','seat'),('CUPRA','cupra')
on conflict(slug) do nothing;
