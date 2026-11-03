-- Public model labels must have verified evidence from a source that is currently permitted for display.
drop policy if exists "anonymous active models read" on public.vehicle_models;
drop policy if exists "authenticated active models read" on public.vehicle_models;

create policy "anonymous active models read"
  on public.vehicle_models for select to anon
  using (
    is_active = true
    and exists (
      select 1
      from public.vehicle_model_source_evidence e
      join public.sources s on s.id = e.source_id
      where e.model_id = vehicle_models.id
        and e.review_status = 'verified'
        and s.permission_status in ('licensed','public_domain')
        and s.attribution_display_enabled = true
    )
  );

create policy "authenticated active models read"
  on public.vehicle_models for select to authenticated
  using (
    (
      is_active = true
      and exists (
        select 1
        from public.vehicle_model_source_evidence e
        join public.sources s on s.id = e.source_id
        where e.model_id = vehicle_models.id
          and e.review_status = 'verified'
          and s.permission_status in ('licensed','public_domain')
          and s.attribution_display_enabled = true
      )
    )
    or private.has_app_role(array['admin','editor','reviewer'])
  );

-- Keep legacy community datasets blocked until their separate data rights are explicitly approved.
update public.sources
set permission_status = 'permission_required',
    attribution_display_enabled = false,
    license_note = concat_ws(E'

', nullif(license_note,''), 'Rights review 2026-11-02: ODbL 1.0 allows commercial reuse only with attribution and share-alike obligations for the adapted public database. The VAG TECH PRO owner has not approved publishing an adapted database under ODbL; keep this source blocked until explicit owner approval or a compatible licensed source is obtained.')
where source_url = 'https://github.com/gor3a/vehicle-makes-models'
  and (
    permission_status in ('licensed','public_domain')
    or attribution_display_enabled is distinct from false
    or position('Rights review 2026-11-02' in coalesce(license_note,'')) = 0
  );

update public.sources
set permission_status = 'permission_required',
    attribution_display_enabled = false,
    license_note = concat_ws(E'

', nullif(license_note,''), 'Rights review 2026-11-02: the repository release labels the project MIT, but the dataset provenance and scope of MIT for the DTC text/database are not established. Repository issue #1 requests clarification of source provenance and commercial redistribution rights. Do not ingest or display DTC data until the author confirms the dataset rights and third-party source permissions. Evidence: https://github.com/Wal33D/dtc-database/issues/1.')
where source_url = 'https://github.com/Wal33D/dtc-database'
  and (
    permission_status in ('licensed','public_domain')
    or attribution_display_enabled is distinct from false
    or position('Rights review 2026-11-02' in coalesce(license_note,'')) = 0
  );

notify pgrst, 'reload schema';