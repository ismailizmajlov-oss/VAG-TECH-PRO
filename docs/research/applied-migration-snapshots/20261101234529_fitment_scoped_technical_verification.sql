-- VAG TECH PRO: second-stage technical verification with exact-fitment gates.

alter table public.document_vehicle_fitment
  add column if not exists status public.record_status not null default 'needs_review';
alter table public.procedure_fitment
  add column if not exists status public.record_status not null default 'needs_review';

alter table public.ingestion_items
  add column if not exists content_review_status text not null default 'pending',
  add column if not exists content_review_note text,
  add column if not exists content_reviewed_by uuid references auth.users(id) on delete set null,
  add column if not exists content_reviewed_at timestamptz;

alter table public.ingestion_items
  add constraint ingestion_items_content_review_status_check
  check (content_review_status in ('pending','verified','rejected')) not valid;
alter table public.ingestion_items
  validate constraint ingestion_items_content_review_status_check;

create index if not exists ingestion_items_content_reviewed_by_idx
  on public.ingestion_items(content_reviewed_by);

drop policy if exists "verified document fitment read" on public.document_vehicle_fitment;
create policy "verified document fitment read"
on public.document_vehicle_fitment for select to anon, authenticated
using (
  status = 'verified'
  and exists (
    select 1
    from public.technical_documents d
    join public.sources ds on ds.id = d.source_id
    where d.id = document_vehicle_fitment.document_id
      and d.status = 'verified'
      and ds.permission_status in ('licensed','public_domain')
  )
  and exists (
    select 1
    from public.vehicle_configurations vc
    join public.sources cs on cs.id = vc.source_id
    where vc.id = document_vehicle_fitment.configuration_id
      and vc.source_status = 'verified'
      and cs.permission_status in ('licensed','public_domain')
  )
);

drop policy if exists "verified procedure fitment read" on public.procedure_fitment;
create policy "verified procedure fitment read"
on public.procedure_fitment for select to anon, authenticated
using (
  status = 'verified'
  and exists (
    select 1
    from public.procedures p
    join public.technical_documents d on d.id = p.document_id
    join public.sources ds on ds.id = d.source_id
    where p.id = procedure_fitment.procedure_id
      and p.status = 'verified'
      and d.status = 'verified'
      and ds.permission_status in ('licensed','public_domain')
  )
  and exists (
    select 1
    from public.vehicle_configurations vc
    join public.sources cs on cs.id = vc.source_id
    where vc.id = procedure_fitment.configuration_id
      and vc.source_status = 'verified'
      and cs.permission_status in ('licensed','public_domain')
  )
);

create or replace function private.review_imported_item(
  p_item_id uuid,
  p_decision text,
  p_note text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_actor uuid := (select auth.uid());
  v_item public.ingestion_items%rowtype;
  v_source_id uuid;
  v_permission text;
  v_document_id uuid;
  v_configuration_id uuid;
  v_procedure_id uuid;
  v_generation_id uuid;
  v_engine_id uuid;
  v_transmission_id uuid;
  v_rows integer;
begin
  if v_actor is null or not private.has_app_role(array['admin','reviewer']) then
    raise exception 'Insufficient role to review imported technical content' using errcode = '42501';
  end if;
  if p_decision is null or p_decision not in ('verify','reject') then
    raise exception 'Decision must be verify or reject' using errcode = '22023';
  end if;

  select * into v_item
  from public.ingestion_items
  where id = p_item_id
  for update;

  if not found then
    raise exception 'Ingestion item not found' using errcode = 'P0002';
  end if;
  if v_item.status <> 'applied' then
    raise exception 'Only imported items can enter technical verification' using errcode = '22023';
  end if;
  if v_item.content_review_status <> 'pending' then
    return jsonb_build_object(
      'status', v_item.content_review_status,
      'already_reviewed', true,
      'item_id', v_item.id
    );
  end if;

  case v_item.record_type
    when 'vehicle_generation' then
      select source_id into v_source_id from public.vehicle_generations where id = v_item.applied_record_id;
    when 'engine' then
      select source_id into v_source_id from public.engines where id = v_item.applied_record_id;
    when 'transmission' then
      select source_id into v_source_id from public.transmissions where id = v_item.applied_record_id;
    when 'vehicle_configuration' then
      select source_id,generation_id,engine_id,transmission_id
        into v_source_id,v_generation_id,v_engine_id,v_transmission_id
      from public.vehicle_configurations where id = v_item.applied_record_id;
    when 'technical_document' then
      select source_id into v_source_id from public.technical_documents where id = v_item.applied_record_id;
    when 'procedure','specification','wiring_diagram','dtc_code','diagnostic_test','document_fitment' then
      select d.source_id into v_source_id
      from public.technical_documents d
      where d.id = nullif(v_item.payload ->> 'document_id','')::uuid;
    when 'procedure_fitment' then
      select d.source_id into v_source_id
      from public.procedures p
      join public.technical_documents d on d.id = p.document_id
      where p.id = nullif(v_item.payload ->> 'procedure_id','')::uuid;
    else
      raise exception 'Unsupported imported record type: %', v_item.record_type using errcode = '22023';
  end case;

  if v_source_id is null then
    raise exception 'The imported record or its parent document is missing' using errcode = 'P0002';
  end if;
  select permission_status into v_permission from public.sources where id = v_source_id;

  if p_decision = 'reject' then
    case v_item.record_type
      when 'vehicle_generation' then update public.vehicle_generations set source_status='rejected' where id=v_item.applied_record_id;
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Target vehicle generation no longer exists' using errcode='P0002'; end if;
      when 'engine' then update public.engines set source_status='rejected' where id=v_item.applied_record_id;
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Target engine no longer exists' using errcode='P0002'; end if;
      when 'transmission' then update public.transmissions set source_status='rejected' where id=v_item.applied_record_id;
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Target transmission no longer exists' using errcode='P0002'; end if;
      when 'vehicle_configuration' then update public.vehicle_configurations set source_status='rejected' where id=v_item.applied_record_id;
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Target configuration no longer exists' using errcode='P0002'; end if;
      when 'technical_document' then update public.technical_documents set status='rejected' where id=v_item.applied_record_id;
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Target document no longer exists' using errcode='P0002'; end if;
      when 'procedure' then update public.procedures set status='rejected' where id=v_item.applied_record_id;
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Target procedure no longer exists' using errcode='P0002'; end if;
      when 'specification' then update public.specifications set status='rejected' where id=v_item.applied_record_id;
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Target specification no longer exists' using errcode='P0002'; end if;
      when 'wiring_diagram' then update public.wiring_diagrams set status='rejected' where id=v_item.applied_record_id;
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Target wiring record no longer exists' using errcode='P0002'; end if;
      when 'dtc_code' then update public.dtc_codes set status='rejected' where id=v_item.applied_record_id;
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Target DTC record no longer exists' using errcode='P0002'; end if;
      when 'diagnostic_test' then update public.diagnostic_tests set status='rejected' where id=v_item.applied_record_id;
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Target diagnostic test no longer exists' using errcode='P0002'; end if;
      when 'document_fitment' then
        update public.document_vehicle_fitment set status='rejected'
        where document_id=(v_item.payload ->> 'document_id')::uuid
          and configuration_id=(v_item.payload ->> 'configuration_id')::uuid;
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Target document fitment no longer exists' using errcode='P0002'; end if;
      when 'procedure_fitment' then
        update public.procedure_fitment set status='rejected'
        where procedure_id=(v_item.payload ->> 'procedure_id')::uuid
          and configuration_id=(v_item.payload ->> 'configuration_id')::uuid;
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Target procedure fitment no longer exists' using errcode='P0002'; end if;
    end case;
  else
    if coalesce(v_permission,'') not in ('licensed','public_domain') then
      raise exception 'The source must remain licensed or public_domain during technical verification' using errcode = '42501';
    end if;

    case v_item.record_type
      when 'vehicle_generation' then
        update public.vehicle_generations set source_status='verified'
        where id=v_item.applied_record_id and source_status='needs_review';
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Vehicle generation is missing or not awaiting review' using errcode='22023'; end if;
      when 'engine' then
        update public.engines set source_status='verified'
        where id=v_item.applied_record_id and source_status='needs_review';
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Engine is missing or not awaiting review' using errcode='22023'; end if;
      when 'transmission' then
        update public.transmissions set source_status='verified'
        where id=v_item.applied_record_id and source_status='needs_review';
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Transmission is missing or not awaiting review' using errcode='22023'; end if;
      when 'vehicle_configuration' then
        if not exists (select 1 from public.vehicle_generations g where g.id=v_generation_id and g.source_status='verified') then
          raise exception 'Generation must be technically verified first' using errcode = '22023';
        end if;
        if v_engine_id is not null and not exists (select 1 from public.engines e where e.id=v_engine_id and e.source_status='verified') then
          raise exception 'Engine must be technically verified first' using errcode = '22023';
        end if;
        if v_transmission_id is not null and not exists (select 1 from public.transmissions t where t.id=v_transmission_id and t.source_status='verified') then
          raise exception 'Transmission must be technically verified first' using errcode = '22023';
        end if;
        update public.vehicle_configurations set source_status='verified'
        where id=v_item.applied_record_id and source_status='needs_review';
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Configuration is missing or not awaiting review' using errcode='22023'; end if;
      when 'document_fitment' then
        v_document_id := (v_item.payload ->> 'document_id')::uuid;
        v_configuration_id := (v_item.payload ->> 'configuration_id')::uuid;
        if not exists (select 1 from public.technical_documents d where d.id=v_document_id and d.status in ('needs_review','verified')) then
          raise exception 'Document must exist and not be rejected' using errcode = '22023';
        end if;
        if not exists (select 1 from public.vehicle_configurations vc join public.sources s on s.id=vc.source_id where vc.id=v_configuration_id and vc.source_status='verified' and s.permission_status in ('licensed','public_domain')) then
          raise exception 'Exact vehicle configuration must be technically verified first' using errcode = '22023';
        end if;
        update public.document_vehicle_fitment set status='verified'
        where document_id=v_document_id and configuration_id=v_configuration_id and status='needs_review';
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Document fitment is missing or not awaiting review' using errcode='22023'; end if;
      when 'technical_document' then
        if not exists (
          select 1 from public.document_vehicle_fitment f
          join public.vehicle_configurations vc on vc.id=f.configuration_id
          join public.sources cs on cs.id=vc.source_id
          where f.document_id=v_item.applied_record_id and f.status='verified'
            and vc.source_status='verified' and cs.permission_status in ('licensed','public_domain')
        ) then
          raise exception 'At least one exact document-to-configuration fitment must be verified first' using errcode = '22023';
        end if;
        update public.technical_documents set status='verified', reviewed_by=v_actor, reviewed_at=now()
        where id=v_item.applied_record_id and status='needs_review';
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Document is missing or not awaiting review' using errcode='22023'; end if;
      when 'procedure_fitment' then
        v_procedure_id := (v_item.payload ->> 'procedure_id')::uuid;
        v_configuration_id := (v_item.payload ->> 'configuration_id')::uuid;
        if not exists (select 1 from public.procedures p join public.technical_documents d on d.id=p.document_id where p.id=v_procedure_id and p.status in ('needs_review','verified') and d.status='verified') then
          raise exception 'Parent document must be verified and procedure must not be rejected' using errcode = '22023';
        end if;
        if not exists (select 1 from public.vehicle_configurations vc join public.sources s on s.id=vc.source_id where vc.id=v_configuration_id and vc.source_status='verified' and s.permission_status in ('licensed','public_domain')) then
          raise exception 'Exact vehicle configuration must be technically verified first' using errcode = '22023';
        end if;
        update public.procedure_fitment set status='verified'
        where procedure_id=v_procedure_id and configuration_id=v_configuration_id and status='needs_review';
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Procedure fitment is missing or not awaiting review' using errcode='22023'; end if;
      when 'procedure' then
        if not exists (select 1 from public.technical_documents d where d.id=(select document_id from public.procedures where id=v_item.applied_record_id) and d.status='verified') then
          raise exception 'Parent technical document must be verified first' using errcode = '22023';
        end if;
        if not exists (
          select 1 from public.procedure_fitment f
          join public.vehicle_configurations vc on vc.id=f.configuration_id
          join public.sources cs on cs.id=vc.source_id
          where f.procedure_id=v_item.applied_record_id and f.status='verified'
            and vc.source_status='verified' and cs.permission_status in ('licensed','public_domain')
        ) then
          raise exception 'At least one exact procedure-to-configuration fitment must be verified first' using errcode = '22023';
        end if;
        update public.procedures set status='verified' where id=v_item.applied_record_id and status='needs_review';
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Procedure is missing or not awaiting review' using errcode='22023'; end if;
      when 'specification' then
        select document_id,configuration_id into v_document_id,v_configuration_id from public.specifications where id=v_item.applied_record_id;
        if not exists (select 1 from public.technical_documents d where d.id=v_document_id and d.status='verified') then
          raise exception 'Parent technical document must be verified first' using errcode = '22023';
        end if;
        if not exists (select 1 from public.vehicle_configurations vc join public.sources s on s.id=vc.source_id where vc.id=v_configuration_id and vc.source_status='verified' and s.permission_status in ('licensed','public_domain')) then
          raise exception 'Exact vehicle configuration must be technically verified first' using errcode = '22023';
        end if;
        update public.specifications set status='verified' where id=v_item.applied_record_id and status='needs_review';
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Specification is missing or not awaiting review' using errcode='22023'; end if;
      when 'wiring_diagram' then
        select document_id,configuration_id into v_document_id,v_configuration_id from public.wiring_diagrams where id=v_item.applied_record_id;
        if not exists (select 1 from public.technical_documents d where d.id=v_document_id and d.status='verified') then
          raise exception 'Parent technical document must be verified first' using errcode = '22023';
        end if;
        if not exists (select 1 from public.vehicle_configurations vc join public.sources s on s.id=vc.source_id where vc.id=v_configuration_id and vc.source_status='verified' and s.permission_status in ('licensed','public_domain')) then
          raise exception 'Exact vehicle configuration must be technically verified first' using errcode = '22023';
        end if;
        update public.wiring_diagrams set status='verified' where id=v_item.applied_record_id and status='needs_review';
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Wiring record is missing or not awaiting review' using errcode='22023'; end if;
      when 'dtc_code' then
        select document_id into v_document_id from public.dtc_codes where id=v_item.applied_record_id;
        if not exists (select 1 from public.technical_documents d where d.id=v_document_id and d.status='verified') then
          raise exception 'Parent technical document must be verified first' using errcode = '22023';
        end if;
        if not exists (
          select 1 from public.document_vehicle_fitment f
          join public.vehicle_configurations vc on vc.id=f.configuration_id
          join public.sources cs on cs.id=vc.source_id
          where f.document_id=v_document_id and f.status='verified'
            and vc.source_status='verified' and cs.permission_status in ('licensed','public_domain')
        ) then
          raise exception 'DTC document must have at least one verified exact vehicle fitment' using errcode = '22023';
        end if;
        update public.dtc_codes set status='verified' where id=v_item.applied_record_id and status='needs_review';
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'DTC record is missing or not awaiting review' using errcode='22023'; end if;
      when 'diagnostic_test' then
        select document_id,configuration_id into v_document_id,v_configuration_id from public.diagnostic_tests where id=v_item.applied_record_id;
        if not exists (select 1 from public.technical_documents d where d.id=v_document_id and d.status='verified') then
          raise exception 'Parent technical document must be verified first' using errcode = '22023';
        end if;
        if not exists (select 1 from public.vehicle_configurations vc join public.sources s on s.id=vc.source_id where vc.id=v_configuration_id and vc.source_status='verified' and s.permission_status in ('licensed','public_domain')) then
          raise exception 'Exact vehicle configuration must be technically verified first' using errcode = '22023';
        end if;
        update public.diagnostic_tests set status='verified' where id=v_item.applied_record_id and status='needs_review';
        get diagnostics v_rows = row_count; if v_rows <> 1 then raise exception 'Diagnostic test is missing or not awaiting review' using errcode='22023'; end if;
    end case;
  end if;

  update public.ingestion_items
  set content_review_status = case when p_decision='verify' then 'verified' else 'rejected' end,
      content_review_note = nullif(left(coalesce(p_note,''),2000),''),
      content_reviewed_by = v_actor,
      content_reviewed_at = now()
  where id=v_item.id;

  return jsonb_build_object(
    'status', case when p_decision='verify' then 'verified' else 'rejected' end,
    'item_id',v_item.id,
    'record_type',v_item.record_type
  );
end;
$$;

revoke all on function private.review_imported_item(uuid,text,text) from public, anon, authenticated;
grant execute on function private.review_imported_item(uuid,text,text) to authenticated;

create or replace function public.review_imported_item(
  p_item_id uuid,
  p_decision text,
  p_note text default null
)
returns jsonb
language sql
security invoker
set search_path = ''
as $$
  select private.review_imported_item(p_item_id,p_decision,p_note);
$$;
revoke all on function public.review_imported_item(uuid,text,text) from public, anon;
grant execute on function public.review_imported_item(uuid,text,text) to authenticated;

notify pgrst, 'reload schema';