#!/usr/bin/env python3
"""Build a separately licensed, candidate-only VAG subset from AutoDiag2/database v6."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPOSITORY = "https://github.com/autodiag2/database"
REVISION = "59b4e774c4023b2daaee179177615f17a5967ae1"
RELEASE_TAG = "v6"
ASSET_URL = "https://github.com/autodiag2/database/releases/download/v6/ad_database.sqlite"
ASSET_SHA256 = "61f9398f479d2d59a8b44c05da72cb5d519232e915bc7dcdf43f4bb5265baaf3"
LICENSE_URL = f"https://raw.githubusercontent.com/autodiag2/database/{REVISION}/LICENSE"
README_URL = f"https://raw.githubusercontent.com/autodiag2/database/{REVISION}/README.md"
LICENSE_GIT_BLOB_SHA1 = "aed5df8b43561cdca41655cba0410cd88350c733"
README_GIT_BLOB_SHA1 = "6f5e088b98130743064bf5204d9d94a62e161bb2"
EXPECTED_ASSET_SIZE = 10649600
MAX_ASSET_BYTES = 20 * 1024 * 1024
VAG_NAMES = {"audi", "volkswagen", "volkswagen__vw_", "skoda", "seat"}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def download(url: str, max_bytes: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "VAG-TECH-PRO-research-builder/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise RuntimeError(f"Download exceeds limit: {url}")
    if not data:
        raise RuntimeError(f"Empty download: {url}")
    return data

def has_table(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None

def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}

def rows(conn: sqlite3.Connection, table: str, where: str = "", params: tuple = ()) -> list[dict]:
    sql = f"SELECT * FROM {table}" + (f" WHERE {where}" if where else "")
    return [dict(row) for row in conn.execute(sql, params)]

def evidence_for(conn: sqlite3.Connection, link_table: str, entity_column: str, entity_id: int | None) -> list[str]:
    if entity_id is None or not has_table(conn, link_table) or not has_table(conn, "ad_evidence"):
        return []
    cols = table_columns(conn, link_table)
    if entity_column not in cols or "evidence_id" not in cols:
        return []
    result = conn.execute(
        f"SELECT e.text FROM {link_table} l JOIN ad_evidence e ON e.id=l.evidence_id "
        f"WHERE l.{entity_column}=? ORDER BY e.id",
        (entity_id,),
    )
    return list(dict.fromkeys(str(row[0]) for row in result if row[0]))

def linked_names(conn: sqlite3.Connection, link_table: str, entity_column: str,
                 entity_id: int, target_table: str, target_id_column: str,
                 target_column: str = "name") -> list[str]:
    if not has_table(conn, link_table) or not has_table(conn, target_table):
        return []
    cols = table_columns(conn, link_table)
    if entity_column not in cols or target_id_column not in cols:
        return []
    result = conn.execute(
        f"SELECT t.{target_column} FROM {link_table} l "
        f"JOIN {target_table} t ON t.id=l.{target_id_column} "
        f"WHERE l.{entity_column}=? ORDER BY t.{target_column}",
        (entity_id,),
    )
    return list(dict.fromkeys(str(row[0]) for row in result if row[0] is not None))

def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def classify_dtc(code: str | None, protocols: list[str], standards: list[str]) -> str:
    value = re.sub(r"\s+", "", str(code or "").upper())
    if not value:
        return "unknown"
    if re.fullmatch(r"P[0-3][0-9A-F]{3}", value):
        second, third = value[1], value[2]
        if second in {"0", "2"} or (second == "3" and third in "456789"):
            return "generic_obd2"
        return "manufacturer_controlled_candidate"
    if re.fullmatch(r"[BCU][0-3][0-9A-F]{3}", value):
        family, second = value[0], value[1]
        if second == "0" or (family == "U" and second == "3"):
            return "generic_obd2"
        if second in {"1", "2"}:
            return "manufacturer_controlled_candidate"
        return "reserved_or_unknown"
    protocol_text = " ".join(protocols + standards).lower()
    if "uds" in protocol_text and re.fullmatch(r"(?:0X)?[0-9A-F]{4,8}", value):
        return "uds_ecu_specific_candidate"
    return "other_or_unknown"

def main() -> None:
    output = Path("research-output/autodiag2-vag-community")
    upstream = output / "upstream"
    upstream.mkdir(parents=True, exist_ok=True)
    temp = Path("research-output/autodiag2-upstream.sqlite")
    temp.parent.mkdir(parents=True, exist_ok=True)

    asset = download(ASSET_URL, MAX_ASSET_BYTES)
    asset_hash = sha256(asset)
    if len(asset) != EXPECTED_ASSET_SIZE:
        raise RuntimeError(f"AutoDiag2 release asset size mismatch: {len(asset)}")
    if asset_hash != ASSET_SHA256:
        raise RuntimeError(f"AutoDiag2 release asset SHA-256 mismatch: {asset_hash}")
    temp.write_bytes(asset)

    license_bytes = download(LICENSE_URL, 100_000)
    readme_bytes = download(README_URL, 200_000)
    license_text = license_bytes.decode("utf-8", errors="strict")
    readme_text = readme_bytes.decode("utf-8", errors="strict")
    if "ODbL-1.0" not in license_text or "DbCL-1.0" not in license_text:
        raise RuntimeError("AutoDiag2 repository license does not declare both ODbL-1.0 and DbCL-1.0")
    def git_blob_sha1(data: bytes) -> str:
        return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\\0" + data).hexdigest()
    if git_blob_sha1(license_bytes) != LICENSE_GIT_BLOB_SHA1 or git_blob_sha1(readme_bytes) != README_GIT_BLOB_SHA1:
        raise RuntimeError("AutoDiag2 LICENSE/README do not match the pinned source revision")
    if "ODbL-1.0" not in readme_text or "DbCL-1.0" not in readme_text:
        raise RuntimeError("AutoDiag2 README does not confirm the database/content license split")
    (upstream / "LICENSE").write_bytes(license_bytes)
    (upstream / "README.md").write_bytes(readme_bytes)

    src = sqlite3.connect(f"file:{temp.resolve().as_posix()}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    integrity = src.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"AutoDiag2 upstream SQLite integrity check failed: {integrity}")

    required = {
        "ad_manufacturer", "ad_vehicle", "ad_vehicle_version", "ad_vehicle_version_config",
        "ad_vehicle_version_config_ecu", "ad_engine", "ad_engine_name", "ad_ecu",
        "ad_dtc", "ad_evidence", "ad_dtc_evidence",
    }
    missing = sorted(name for name in required if not has_table(src, name))
    if missing:
        raise RuntimeError("AutoDiag2 upstream schema is missing required tables: " + ", ".join(missing))

    manufacturer_rows = rows(src, "ad_manufacturer")
    manufacturers = {int(r["id"]): str(r["name"]) for r in manufacturer_rows}
    vag_manufacturers = {mid: name for mid, name in manufacturers.items() if name.casefold() in VAG_NAMES}
    if len(vag_manufacturers) < 4:
        raise RuntimeError("Could not resolve at least four VAG makes in the pinned source database")

    placeholders = ",".join("?" for _ in vag_manufacturers)
    vag_ids = tuple(vag_manufacturers.keys())
    vehicles = rows(src, "ad_vehicle", f"manufacturer_id IN ({placeholders})", vag_ids)
    vehicle_by_id = {int(r["id"]): r for r in vehicles}
    vehicle_ids = tuple(vehicle_by_id)
    if not vehicle_ids:
        raise RuntimeError("AutoDiag2 VAG vehicle subset is empty")

    vph = ",".join("?" for _ in vehicle_ids)
    versions = rows(src, "ad_vehicle_version", f"vehicle_id IN ({vph})", vehicle_ids)
    version_by_id = {int(r["id"]): r for r in versions}
    version_ids = tuple(version_by_id)
    vph2 = ",".join("?" for _ in version_ids) or "NULL"
    configs = rows(src, "ad_vehicle_version_config", f"vehicle_version_id IN ({vph2})", version_ids)
    config_by_id = {int(r["id"]): r for r in configs}
    config_ids = tuple(config_by_id)

    ecu_links = []
    if config_ids and has_table(src, "ad_vehicle_version_config_ecu"):
        cph = ",".join("?" for _ in config_ids)
        ecu_links = rows(src, "ad_vehicle_version_config_ecu", f"config_id IN ({cph})", config_ids)
    ecu_ids = tuple(sorted({int(r["ecu_id"]) for r in ecu_links}))
    eph = ",".join("?" for _ in ecu_ids) or "NULL"
    ecus = rows(src, "ad_ecu", f"id IN ({eph})", ecu_ids) if has_table(src, "ad_ecu") else []
    ecu_by_id = {int(r["id"]): r for r in ecus}
    mcu_ids = tuple(sorted({int(r["mcu_id"]) for r in ecus if r.get("mcu_id") is not None}))
    mph = ",".join("?" for _ in mcu_ids) or "NULL"
    mcus = rows(src, "ad_mcu", f"id IN ({mph})", mcu_ids) if mcu_ids and has_table(src, "ad_mcu") else []
    mcu_by_id = {int(r["id"]): r for r in mcus}

    engine_ids = tuple(sorted({int(r["engine_id"]) for r in configs if r.get("engine_id") is not None}))
    engph = ",".join("?" for _ in engine_ids) or "NULL"
    engines = rows(src, "ad_engine", f"id IN ({engph})", engine_ids) if engine_ids else []
    engine_by_id = {int(r["id"]): r for r in engines}

    def manufacturer_name(manufacturer_id) -> str | None:
        if manufacturer_id is None:
            return None
        return manufacturers.get(int(manufacturer_id))

    def engine_names(engine_id: int | None) -> list[str]:
        if engine_id is None or not has_table(src, "ad_engine_name"):
            return []
        return [str(r[0]) for r in src.execute(
            "SELECT name FROM ad_engine_name WHERE engine_id=? ORDER BY name", (engine_id,)
        )]

    def protocol_params(protocol_id: int) -> list[dict]:
        if not has_table(src, "ad_vehicle_version_config_ecu_protocol_param"):
            return []
        return [dict(r) for r in src.execute(
            "SELECT name,value_text,value_integer,value_real FROM ad_vehicle_version_config_ecu_protocol_param "
            "WHERE protocol_id=? ORDER BY name", (protocol_id,)
        )]

    ecu_links_by_config: dict[int, list[dict]] = {}
    for link in ecu_links:
        ecu_links_by_config.setdefault(int(link["config_id"]), []).append(link)

    protocol_by_ecu_link: dict[int, list[dict]] = {}
    if has_table(src, "ad_vehicle_version_config_ecu_protocol"):
        link_ids = tuple(int(r["id"]) for r in ecu_links)
        if link_ids:
            lph = ",".join("?" for _ in link_ids)
            for protocol_row in rows(
                src, "ad_vehicle_version_config_ecu_protocol",
                f"vehicle_version_config_ecu_id IN ({lph})", link_ids
            ):
                protocol_by_ecu_link.setdefault(int(protocol_row["vehicle_version_config_ecu_id"]), []).append(
                    {**protocol_row, "params": protocol_params(int(protocol_row["id"]))}
                )

    out_db = output / "autodiag2-vag-community.sqlite"
    if out_db.exists():
        out_db.unlink()
    dst = sqlite3.connect(out_db)
    dst.row_factory = sqlite3.Row
    dst.execute("PRAGMA foreign_keys=ON")
    dst.execute("PRAGMA journal_mode=DELETE")
    dst.execute("PRAGMA synchronous=FULL")
    dst.executescript("""
      CREATE TABLE source_registry (
        source_id TEXT PRIMARY KEY,
        publisher TEXT NOT NULL,
        repository_url TEXT NOT NULL,
        release_tag TEXT NOT NULL,
        source_revision TEXT NOT NULL,
        source_asset_url TEXT NOT NULL,
        source_asset_sha256 TEXT NOT NULL,
        database_license TEXT NOT NULL,
        contents_license TEXT NOT NULL,
        license_sha256 TEXT NOT NULL,
        readme_sha256 TEXT NOT NULL,
        market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
        verification_status TEXT NOT NULL CHECK(verification_status='community_reference_unverified'),
        share_alike_required INTEGER NOT NULL CHECK(share_alike_required=1),
        attribution_required INTEGER NOT NULL CHECK(attribution_required=1),
        diagnostic_execution_allowed INTEGER NOT NULL CHECK(diagnostic_execution_allowed=0),
        exact_fitment_claim INTEGER NOT NULL CHECK(exact_fitment_claim=0)
      );
      CREATE TABLE vehicle_model_candidates (
        upstream_vehicle_id INTEGER PRIMARY KEY,
        make TEXT NOT NULL,
        source_make TEXT NOT NULL,
        make_alias_status TEXT NOT NULL,
        model TEXT NOT NULL,
        vehicle_type TEXT,
        evidence_json TEXT NOT NULL,
        upstream_payload_json TEXT NOT NULL,
        market_scope TEXT NOT NULL DEFAULT 'UNKNOWN',
        verification_status TEXT NOT NULL DEFAULT 'community_reference_unverified'
      );
      CREATE TABLE vehicle_version_candidates (
        upstream_version_id INTEGER PRIMARY KEY,
        upstream_vehicle_id INTEGER NOT NULL,
        make TEXT NOT NULL,
        model TEXT NOT NULL,
        version_label TEXT,
        year_label TEXT,
        evidence_json TEXT NOT NULL,
        upstream_payload_json TEXT NOT NULL,
        market_scope TEXT NOT NULL DEFAULT 'UNKNOWN',
        verification_status TEXT NOT NULL DEFAULT 'community_reference_unverified',
        FOREIGN KEY(upstream_vehicle_id) REFERENCES vehicle_model_candidates(upstream_vehicle_id)
      );
      CREATE TABLE engine_candidates (
        upstream_engine_id INTEGER PRIMARY KEY,
        source_make TEXT,
        engine_code TEXT,
        engine_code_quality TEXT NOT NULL,
        fuel TEXT,
        names_json TEXT NOT NULL,
        evidence_json TEXT NOT NULL,
        upstream_payload_json TEXT NOT NULL,
        market_scope TEXT NOT NULL DEFAULT 'UNKNOWN',
        verification_status TEXT NOT NULL DEFAULT 'community_reference_unverified'
      );
      CREATE TABLE ecu_candidates (
        upstream_ecu_id INTEGER PRIMARY KEY,
        ecu_manufacturer TEXT,
        ecu_model TEXT NOT NULL,
        ecu_type TEXT,
        mcu_manufacturer TEXT,
        mcu_model TEXT,
        mcu_type TEXT,
        evidence_json TEXT NOT NULL,
        upstream_payload_json TEXT NOT NULL,
        verification_status TEXT NOT NULL DEFAULT 'community_reference_unverified'
      );
      CREATE TABLE vehicle_config_candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        upstream_config_id INTEGER NOT NULL,
        upstream_ecu_link_id INTEGER,
        upstream_vehicle_id INTEGER NOT NULL,
        upstream_version_id INTEGER NOT NULL,
        upstream_engine_id INTEGER,
        upstream_ecu_id INTEGER,
        make TEXT NOT NULL,
        model TEXT NOT NULL,
        version_label TEXT,
        year_label TEXT,
        engine_code TEXT,
        engine_fuel TEXT,
        power_kw REAL,
        ecu_manufacturer TEXT,
        ecu_model TEXT,
        ecu_type TEXT,
        protocols_json TEXT NOT NULL,
        protocol_params_json TEXT NOT NULL,
        evidence_json TEXT NOT NULL,
        market_scope TEXT NOT NULL DEFAULT 'UNKNOWN',
        applicability_precision TEXT NOT NULL DEFAULT 'community_vehicle_version_ecu_candidate',
        verification_status TEXT NOT NULL DEFAULT 'community_reference_unverified',
        exact_fitment_claim INTEGER NOT NULL DEFAULT 0 CHECK(exact_fitment_claim=0),
        diagnostic_execution_allowed INTEGER NOT NULL DEFAULT 0 CHECK(diagnostic_execution_allowed=0),
        FOREIGN KEY(upstream_vehicle_id) REFERENCES vehicle_model_candidates(upstream_vehicle_id),
        FOREIGN KEY(upstream_version_id) REFERENCES vehicle_version_candidates(upstream_version_id),
        FOREIGN KEY(upstream_engine_id) REFERENCES engine_candidates(upstream_engine_id),
        FOREIGN KEY(upstream_ecu_id) REFERENCES ecu_candidates(upstream_ecu_id)
      );
      CREATE TABLE dtc_candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        upstream_dtc_id INTEGER NOT NULL,
        source_scope TEXT NOT NULL CHECK(source_scope IN ('vehicle_ecu_linked','make_level')),
        make_labels_json TEXT NOT NULL,
        upstream_ecu_id INTEGER NOT NULL,
        ecu_manufacturer TEXT,
        ecu_model TEXT NOT NULL,
        code TEXT NOT NULL,
        namespace TEXT NOT NULL CHECK(namespace IN ('manufacturer_controlled_candidate','uds_ecu_specific_candidate')),
        definition TEXT,
        description TEXT,
        mil INTEGER,
        detection_condition TEXT,
        causes TEXT,
        repairs TEXT,
        standards_json TEXT NOT NULL,
        protocols_json TEXT NOT NULL,
        evidence_json TEXT NOT NULL,
        evidence_count INTEGER NOT NULL CHECK(evidence_count>0),
        repair_text_status TEXT NOT NULL DEFAULT 'community_unverified_not_actionable',
        market_scope TEXT NOT NULL DEFAULT 'UNKNOWN',
        applicability_precision TEXT NOT NULL,
        verification_status TEXT NOT NULL DEFAULT 'community_reference_unverified',
        exact_vehicle_fitment_claim INTEGER NOT NULL DEFAULT 0 CHECK(exact_vehicle_fitment_claim=0),
        ecu_fitment_claim INTEGER NOT NULL DEFAULT 0 CHECK(ecu_fitment_claim=0),
        diagnostic_execution_allowed INTEGER NOT NULL DEFAULT 0 CHECK(diagnostic_execution_allowed=0),
        repair_advice_approved INTEGER NOT NULL DEFAULT 0 CHECK(repair_advice_approved=0),
        upstream_payload_json TEXT NOT NULL,
        UNIQUE(upstream_dtc_id,source_scope,upstream_ecu_id)
      );
      CREATE TABLE dtc_fitment_candidates (
        dtc_candidate_id INTEGER NOT NULL,
        vehicle_config_candidate_id INTEGER NOT NULL,
        upstream_dtc_id INTEGER NOT NULL,
        upstream_config_id INTEGER NOT NULL,
        upstream_ecu_link_id INTEGER NOT NULL,
        make TEXT NOT NULL,
        model TEXT NOT NULL,
        version_label TEXT,
        year_label TEXT,
        engine_code TEXT,
        power_kw REAL,
        ecu_model TEXT NOT NULL,
        fitment_status TEXT NOT NULL DEFAULT 'community_reference_candidate',
        market_scope TEXT NOT NULL DEFAULT 'UNKNOWN',
        exact_fitment_claim INTEGER NOT NULL DEFAULT 0 CHECK(exact_fitment_claim=0),
        PRIMARY KEY(dtc_candidate_id,vehicle_config_candidate_id),
        FOREIGN KEY(dtc_candidate_id) REFERENCES dtc_candidates(id),
        FOREIGN KEY(vehicle_config_candidate_id) REFERENCES vehicle_config_candidates(id)
      );
      CREATE INDEX idx_vag_dtc_code ON dtc_candidates(code);
      CREATE INDEX idx_vag_dtc_namespace ON dtc_candidates(namespace,source_scope);
      CREATE INDEX idx_vag_vehicle_model ON vehicle_model_candidates(make,model);
      CREATE INDEX idx_vag_engine_code ON engine_candidates(engine_code);
      CREATE INDEX idx_vag_config_make_model ON vehicle_config_candidates(make,model);
    """)

    dst.execute(
        "INSERT INTO source_registry VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "autodiag2-vag-community-v6", "AutoDiag2/database", REPOSITORY, RELEASE_TAG, REVISION,
            ASSET_URL, asset_hash, "ODbL-1.0", "DbCL-1.0", sha256(license_bytes), sha256(readme_bytes),
            "UNKNOWN", "community_reference_unverified", 1, 1, 0, 0
        )
    )

    make_alias = {name: ("alias_candidate" if name.casefold() == "volkswagen__vw_" else "source_name") for name in vag_manufacturers.values()}
    for vehicle in vehicles:
        make = manufacturers[int(vehicle["manufacturer_id"])]
        dst.execute(
            "INSERT INTO vehicle_model_candidates VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                int(vehicle["id"]), "Volkswagen" if make.casefold()=="volkswagen__vw_" else make,
                make, make_alias[make], vehicle["model"], vehicle.get("type"),
                json_text(evidence_for(src,"ad_vehicle_evidence","vehicle_id",int(vehicle["id"]))),
                json_text(vehicle), "UNKNOWN", "community_reference_unverified"
            )
        )

    for version in versions:
        vehicle = vehicle_by_id[int(version["vehicle_id"])]
        make = manufacturers[int(vehicle["manufacturer_id"])]
        dst.execute(
            "INSERT INTO vehicle_version_candidates VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                int(version["id"]), int(vehicle["id"]),
                "Volkswagen" if make.casefold()=="volkswagen__vw_" else make,
                vehicle["model"], version.get("version"), version.get("year"),
                json_text(evidence_for(src,"ad_vehicle_version_evidence","vehicle_version_id",int(version["id"]))),
                json_text(version), "UNKNOWN", "community_reference_unverified"
            )
        )

    for engine in engines:
        engine_id = int(engine["id"])
        code = str(engine.get("code") or "")
        quality = "factory_code_shape_candidate" if re.fullmatch(r"[A-Z0-9]{3,5}", code.upper()) else "unclassified_source_label"
        dst.execute(
            "INSERT INTO engine_candidates VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                engine_id, manufacturer_name(engine.get("manufacturer_id")), code or None, quality,
                engine.get("fuel"), json_text(engine_names(engine_id)),
                json_text(evidence_for(src,"ad_engine_evidence","engine_id",engine_id)),
                json_text(engine), "UNKNOWN", "community_reference_unverified"
            )
        )

    for ecu in ecus:
        ecu_id = int(ecu["id"])
        mcu = mcu_by_id.get(int(ecu["mcu_id"])) if ecu.get("mcu_id") is not None else None
        dst.execute(
            "INSERT INTO ecu_candidates VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                ecu_id, manufacturer_name(ecu.get("manufacturer_id")), ecu["model"], ecu.get("type"),
                manufacturer_name(mcu.get("manufacturer_id")) if mcu else None,
                mcu.get("model") if mcu else None, mcu.get("type") if mcu else None,
                json_text(evidence_for(src,"ad_ecu_evidence","ecu_id",ecu_id)),
                json_text(ecu), "community_reference_unverified"
            )
        )

    config_row_id: dict[tuple[int,int | None], int] = {}
    config_ecu_id_by_link: dict[int,int] = {}
    for config in configs:
        version = version_by_id[int(config["vehicle_version_id"])]
        vehicle = vehicle_by_id[int(version["vehicle_id"])]
        make_source = manufacturers[int(vehicle["manufacturer_id"])]
        make = "Volkswagen" if make_source.casefold()=="volkswagen__vw_" else make_source
        engine = engine_by_id.get(int(config["engine_id"])) if config.get("engine_id") is not None else None
        links = ecu_links_by_config.get(int(config["id"]), []) or [None]
        for link in links:
            ecu = ecu_by_id.get(int(link["ecu_id"])) if link else None
            ecu_id = int(ecu["id"]) if ecu else None
            protocols = protocol_by_ecu_link.get(int(link["id"]), []) if link else []
            protocol_names = [str(p["protocol"]) for p in protocols]
            params = [p.get("params", []) for p in protocols]
            evidence = []
            evidence.extend(evidence_for(src,"ad_vehicle_version_config_evidence","config_id",int(config["id"])))
            evidence.extend(evidence_for(src,"ad_vehicle_evidence","vehicle_id",int(vehicle["id"])))
            evidence.extend(evidence_for(src,"ad_vehicle_version_evidence","vehicle_version_id",int(version["id"])))
            if engine:
                evidence.extend(evidence_for(src,"ad_engine_evidence","engine_id",int(engine["id"])))
            if ecu:
                evidence.extend(evidence_for(src,"ad_ecu_evidence","ecu_id",int(ecu["id"])))
            mcu = mcu_by_id.get(int(ecu["mcu_id"])) if ecu and ecu.get("mcu_id") is not None else None
            if mcu:
                evidence.extend(evidence_for(src,"ad_mcu_evidence","mcu_id",int(mcu["id"])))
            cur = dst.execute(
                "INSERT INTO vehicle_config_candidates(upstream_config_id,upstream_ecu_link_id,upstream_vehicle_id,upstream_version_id,upstream_engine_id,upstream_ecu_id,make,model,version_label,year_label,engine_code,engine_fuel,power_kw,ecu_manufacturer,ecu_model,ecu_type,protocols_json,protocol_params_json,evidence_json,market_scope,applicability_precision,verification_status,exact_fitment_claim,diagnostic_execution_allowed) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,0)",
                (
                    int(config["id"]), int(link["id"]) if link else None, int(vehicle["id"]), int(version["id"]),
                    int(engine["id"]) if engine else None, ecu_id, make, vehicle["model"], version.get("version"),
                    version.get("year"), engine.get("code") if engine else None, engine.get("fuel") if engine else None,
                    config.get("power_kw"), manufacturer_name(ecu.get("manufacturer_id")) if ecu else None,
                    ecu.get("model") if ecu else None, ecu.get("type") if ecu else None,
                    json_text(protocol_names), json_text(params), json_text(list(dict.fromkeys(evidence))),
                    "UNKNOWN", "community_vehicle_version_ecu_candidate", "community_reference_unverified"
                )
            )
            config_row_id[(int(config["id"]), int(link["id"]) if link else None)] = int(cur.lastrowid)
            if link:
                config_ecu_id_by_link[int(link["id"])] = int(cur.lastrowid)

    dtc_rows = rows(src, "ad_dtc")
    dtc_by_id = {int(r["id"]): r for r in dtc_rows}
    vag_ecu_id_set = set(ecu_ids)
    make_labels_by_ecu: dict[int,set[str]] = {}
    config_links_by_ecu: dict[int,list[dict]] = {}
    for link in ecu_links:
        ecu_id = int(link["ecu_id"])
        config = config_by_id[int(link["config_id"])]
        version = version_by_id[int(config["vehicle_version_id"])]
        vehicle = vehicle_by_id[int(version["vehicle_id"])]
        make_source = manufacturers[int(vehicle["manufacturer_id"])]
        make = "Volkswagen" if make_source.casefold()=="volkswagen__vw_" else make_source
        make_labels_by_ecu.setdefault(ecu_id,set()).add(make)
        config_links_by_ecu.setdefault(ecu_id,[]).append(link)

    included_dtc_ids: set[int] = set()
    excluded = {"generic_obd2":0,"no_evidence":0,"other_or_unknown":0,"empty_description":0}
    for dtc in dtc_rows:
        ecu_id = int(dtc["ecu_id"])
        if ecu_id not in vag_ecu_id_set:
            continue
        dtc_id = int(dtc["id"])
        evidence = evidence_for(src,"ad_dtc_evidence","dtc_id",dtc_id)
        if not evidence:
            excluded["no_evidence"] += 1
            continue
        protocols = linked_names(src,"ad_dtc_protocol_link","dtc_id",dtc_id,"ad_diag_protocol","protocol_id")
        standards = linked_names(src,"ad_dtc_standard_link","dtc_id",dtc_id,"ad_dtc_standard","standard_id")
        namespace = classify_dtc(dtc.get("code"),protocols,standards)
        if namespace == "generic_obd2":
            excluded["generic_obd2"] += 1
            continue
        if namespace not in {"manufacturer_controlled_candidate","uds_ecu_specific_candidate"}:
            excluded["other_or_unknown"] += 1
            continue
        if not (dtc.get("definition") or dtc.get("description")):
            excluded["empty_description"] += 1
            continue
        ecu = ecu_by_id[ecu_id]
        cur = dst.execute(
            "INSERT INTO dtc_candidates(upstream_dtc_id,source_scope,make_labels_json,upstream_ecu_id,ecu_manufacturer,ecu_model,code,namespace,definition,description,mil,detection_condition,causes,repairs,standards_json,protocols_json,evidence_json,evidence_count,repair_text_status,market_scope,applicability_precision,verification_status,exact_vehicle_fitment_claim,ecu_fitment_claim,diagnostic_execution_allowed,repair_advice_approved,upstream_payload_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,0,0,0,?)",
            (
                dtc_id,"vehicle_ecu_linked",json_text(sorted(make_labels_by_ecu.get(ecu_id,set()))),ecu_id,
                manufacturer_name(ecu.get("manufacturer_id")),ecu["model"],dtc.get("code"),namespace,
                dtc.get("definition"),dtc.get("description"),dtc.get("mil"),dtc.get("detection_condition"),
                dtc.get("causes"),dtc.get("repairs"),json_text(standards),json_text(protocols),
                json_text(evidence),len(evidence),"community_unverified_not_actionable","UNKNOWN",
                "community_vehicle_version_ecu_candidate","community_reference_unverified",json_text(dtc)
            )
        )
        included_dtc_ids.add(dtc_id)
        candidate_id = int(cur.lastrowid)
        for link in config_links_by_ecu.get(ecu_id,[]):
            config = config_by_id[int(link["config_id"])]
            version = version_by_id[int(config["vehicle_version_id"])]
            vehicle = vehicle_by_id[int(version["vehicle_id"])]
            make_source = manufacturers[int(vehicle["manufacturer_id"])]
            make = "Volkswagen" if make_source.casefold()=="volkswagen__vw_" else make_source
            engine = engine_by_id.get(int(config["engine_id"])) if config.get("engine_id") is not None else None
            config_candidate_id = config_ecu_id_by_link[int(link["id"])]
            dst.execute(
                "INSERT INTO dtc_fitment_candidates(dtc_candidate_id,vehicle_config_candidate_id,upstream_dtc_id,upstream_config_id,upstream_ecu_link_id,make,model,version_label,year_label,engine_code,power_kw,ecu_model) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    candidate_id,config_candidate_id,dtc_id,int(config["id"]),int(link["id"]),make,
                    vehicle["model"],version.get("version"),version.get("year"),
                    engine.get("code") if engine else None,config.get("power_kw"),ecu_by_id[ecu_id]["model"]
                )
            )

    generic_mfr_ids = tuple(mid for mid,name in manufacturers.items() if name.casefold() in {"generic","generic_ecu"})
    make_level_ecus = []
    if generic_mfr_ids:
        gph = ",".join("?" for _ in generic_mfr_ids)
        make_level_ecus = rows(src,"ad_ecu",f"manufacturer_id IN ({gph})",generic_mfr_ids)
    make_aliases = {name.casefold():name for name in vag_manufacturers.values()}
    for ecu in make_level_ecus:
        make_label = str(ecu.get("model") or "").casefold()
        if make_label not in make_aliases:
            continue
        make_name = make_aliases[make_label]
        ecu_id = int(ecu["id"])
        for dtc in rows(src,"ad_dtc","ecu_id=?",(ecu_id,)):
            dtc_id = int(dtc["id"])
            evidence = evidence_for(src,"ad_dtc_evidence","dtc_id",dtc_id)
            if not evidence:
                continue
            protocols = linked_names(src,"ad_dtc_protocol_link","dtc_id",dtc_id,"ad_diag_protocol")
            standards = linked_names(src,"ad_dtc_standard_link","dtc_id",dtc_id,"ad_dtc_standard")
            namespace = classify_dtc(dtc.get("code"),protocols,standards)
            if namespace != "manufacturer_controlled_candidate" or not (dtc.get("definition") or dtc.get("description")):
                continue
            if dtc_id in included_dtc_ids:
                continue
            dst.execute(
                "INSERT OR IGNORE INTO dtc_candidates(upstream_dtc_id,source_scope,make_labels_json,upstream_ecu_id,ecu_manufacturer,ecu_model,code,namespace,definition,description,mil,detection_condition,causes,repairs,standards_json,protocols_json,evidence_json,evidence_count,repair_text_status,market_scope,applicability_precision,verification_status,exact_vehicle_fitment_claim,ecu_fitment_claim,diagnostic_execution_allowed,repair_advice_approved,upstream_payload_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,0,0,0,?)",
                (
                    dtc_id,"make_level",json_text([make_name]),ecu_id,manufacturer_name(ecu.get("manufacturer_id")),
                    ecu["model"],dtc.get("code"),namespace,dtc.get("definition"),dtc.get("description"),
                    dtc.get("mil"),dtc.get("detection_condition"),dtc.get("causes"),dtc.get("repairs"),
                    json_text(standards),json_text(protocols),json_text(evidence),len(evidence),
                    "community_unverified_not_actionable","UNKNOWN","manufacturer_make_candidate",
                    "community_reference_unverified",json_text(dtc)
                )
            )

    dst.commit()
    dst_integrity = dst.execute("PRAGMA integrity_check").fetchone()[0]
    fk_issues = list(dst.execute("PRAGMA foreign_key_check"))
    if dst_integrity != "ok" or fk_issues:
        raise RuntimeError(f"Candidate pack integrity failure: {dst_integrity}; FK issues={len(fk_issues)}")
    counts = {
        "vehicle_models": dst.execute("SELECT COUNT(*) FROM vehicle_model_candidates").fetchone()[0],
        "vehicle_versions": dst.execute("SELECT COUNT(*) FROM vehicle_version_candidates").fetchone()[0],
        "engines": dst.execute("SELECT COUNT(*) FROM engine_candidates").fetchone()[0],
        "ecus": dst.execute("SELECT COUNT(*) FROM ecu_candidates").fetchone()[0],
        "vehicle_config_candidates": dst.execute("SELECT COUNT(*) FROM vehicle_config_candidates").fetchone()[0],
        "dtc_candidates": dst.execute("SELECT COUNT(*) FROM dtc_candidates").fetchone()[0],
        "vehicle_ecu_linked_dtc_candidates": dst.execute("SELECT COUNT(*) FROM dtc_candidates WHERE source_scope='vehicle_ecu_linked'").fetchone()[0],
        "make_level_dtc_candidates": dst.execute("SELECT COUNT(*) FROM dtc_candidates WHERE source_scope='make_level'").fetchone()[0],
        "dtc_fitment_candidate_links": dst.execute("SELECT COUNT(*) FROM dtc_fitment_candidates").fetchone()[0],
        "generic_dtc_rows_in_pack": dst.execute("SELECT COUNT(*) FROM dtc_candidates WHERE namespace='generic_obd2'").fetchone()[0],
        "transmission_records": 0
    }
    dst.close()
    src.close()

    if counts["generic_dtc_rows_in_pack"] != 0:
        raise RuntimeError("Generic SAE/ISO DTC rows leaked into the VAG candidate pack")
    if counts["vehicle_models"] == 0 or counts["engines"] == 0:
        raise RuntimeError("AutoDiag2 VAG candidate pack unexpectedly has no vehicle models or engines")

    db_hash = sha256(out_db.read_bytes())
    attribution = (
        "Contains a filtered candidate subset from AutoDiag2/database, release v6, "
        "https://github.com/autodiag2/database. Source database licensed under ODbL-1.0; "
        "database contents licensed under DbCL-1.0. This derived database is distributed under ODbL-1.0 "
        "and must remain available under that license when publicly conveyed. Attribution and source links "
        "are preserved in this pack. Upstream data is community-contributed and is not an OEM repair manual. "
        "All records are unverified candidates; market scope is UNKNOWN. No diagnostic execution is enabled. "
        "No gearbox/transmission mapping is supplied by this source schema."
    )
    (output / "ATTRIBUTION.txt").write_text(attribution + "\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "pack_id": "autodiag2-vag-community-v6",
        "publisher": "AutoDiag2/database",
        "repository_url": REPOSITORY,
        "release_tag": RELEASE_TAG,
        "source_revision": REVISION,
        "source_asset_url": ASSET_URL,
        "source_asset_sha256": asset_hash,
        "source_asset_size_bytes": len(asset),
        "license": {
            "database": "ODbL-1.0",
            "database_uri": "https://opendatacommons.org/licenses/odbl/1-0/",
            "contents": "DbCL-1.0",
            "contents_uri": "https://opendatacommons.org/licenses/dbcl/1-0/",
            "license_file_sha256": sha256(license_bytes),
            "readme_sha256": sha256(readme_bytes),
            "share_alike_required": True,
            "attribution_required": True,
            "commercial_use_allowed": True,
            "display_allowed": True,
            "offline_cache_allowed": True,
            "redistribution_allowed": True,
            "separate_pack_required": True
        },
        "market_scope": "UNKNOWN",
        "verification_status": "community_reference_unverified",
        "display_status": "candidate_only_not_oem_verified",
        "applicability_precision": "community_vehicle_version_ecu_candidate",
        "exact_vehicle_fitment": False,
        "ecu_fitment": False,
        "diagnostic_execution_allowed": False,
        "repair_advice_approved": False,
        "generic_dtc_mixed_into_vag_pack": False,
        "transmission_data_present": False,
        "counts": counts,
        "excluded_dtc_counts": excluded,
        "vag_source_make_names": sorted(vag_manufacturers.values()),
        "make_alias_note": "Volkswagen__VW_ is preserved as a source label and marked alias_candidate; it is not merged into Volkswagen records.",
        "upstream_sqlite_integrity": integrity,
        "candidate_sqlite_integrity": dst_integrity,
        "candidate_sqlite_foreign_key_issues": len(fk_issues),
        "candidate_database_sha256": db_hash,
        "created_at_utc": datetime.now(timezone.utc).isoformat()
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = [
        ("autodiag2-vag-community.sqlite", db_hash),
        ("manifest.json", sha256(manifest_path.read_bytes())),
        ("ATTRIBUTION.txt", sha256((output / "ATTRIBUTION.txt").read_bytes())),
        ("upstream/LICENSE", sha256(license_bytes)),
        ("upstream/README.md", sha256(readme_bytes))
    ]
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in files), encoding="utf-8"
    )
    print("AUTODIAG2_VAG_PACK_REPORT=" + json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    temp.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
