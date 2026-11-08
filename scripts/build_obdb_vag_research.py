#!/usr/bin/env python3
"""Build a pinned, read-only OBDb VAG signal research pack. No ECU commands are executed."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import sys
import urllib.parse
import urllib.request
from pathlib import Path

MANIFEST_PATH = Path("data/source-manifests/obdb-vag-signalsets.json")
MAX_FILE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_BYTES = 96 * 1024 * 1024
USER_AGENT = "VAG-TECH-PRO-OBDb-Research-Pack/1.0"
SOURCE_PATHS = (
    "LICENSE",
    "README.md",
    "generations.yaml",
    "signalsets/v3/default.json",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fetch_pinned(repository: str, commit: str, relative_path: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Source commit must be a full 40-character SHA")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", relative_path) or ".." in relative_path.split("/"):
        raise ValueError("Unsafe upstream path")
    url = f"https://raw.githubusercontent.com/{repository}/{commit}/{relative_path}"
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "raw.githubusercontent.com":
        raise ValueError("Only pinned raw.githubusercontent.com sources are allowed")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream"})
    with urllib.request.urlopen(request, timeout=35) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != "raw.githubusercontent.com":
            raise ValueError("Upstream redirected outside the approved raw GitHub host")
        payload = response.read(MAX_FILE_BYTES + 1)
    if not payload or len(payload) > MAX_FILE_BYTES:
        raise ValueError(f"Upstream file is empty or exceeds {MAX_FILE_BYTES} bytes: {relative_path}")
    return payload


def parse_year(value: str | None) -> int | None:
    if value is None:
        return None
    token = value.strip().strip('"').strip("'")
    if token.lower() in {"", "null", "none", "~"}:
        return None
    if not re.fullmatch(r"\d{4}", token):
        raise ValueError(f"Unexpected generation year value: {value}")
    return int(token)


def parse_generation_candidates(text: str, default_reference: str) -> list[dict]:
    generations: list[dict] = []
    current: dict | None = None
    reference_urls: list[str] = []
    in_generations = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped == "generations:":
            in_generations = True
            continue
        if not in_generations and stripped.startswith('- "') and "http" in stripped:
            match = re.search(r"https?://[^\"']+", stripped)
            if match:
                reference_urls.append(match.group(0))
        if not in_generations:
            continue
        if stripped.startswith("- name:"):
            if current:
                generations.append(current)
            name = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            if not name:
                raise ValueError("Empty generation name")
            current = {"name": name, "year_start": None, "year_end": None, "raw_line": raw_line.strip()}
        elif current and stripped.startswith("start_year:"):
            current["year_start"] = parse_year(stripped.split(":", 1)[1])
        elif current and stripped.startswith("end_year:"):
            current["year_end"] = parse_year(stripped.split(":", 1)[1])
    if current:
        generations.append(current)
    reference = reference_urls[0] if reference_urls else default_reference
    for item in generations:
        item["reference_url"] = reference
    return generations


def validate_hex(value: object, label: str, exact_len: int | None = None, min_len: int | None = None, max_len: int | None = None) -> str:
    token = str(value or "").strip().upper()
    if not re.fullmatch(r"[0-9A-F]+", token):
        raise ValueError(f"Invalid hexadecimal {label}: {value}")
    if exact_len is not None and len(token) != exact_len:
        raise ValueError(f"Invalid length for {label}: {value}")
    if min_len is not None and len(token) < min_len:
        raise ValueError(f"Value too short for {label}: {value}")
    if max_len is not None and len(token) > max_len:
        raise ValueError(f"Value too long for {label}: {value}")
    return token


def finite_json(value: object, label: str) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Non-JSON or non-finite value in {label}") from exc


def validate_signalset(document: object, source_id: str) -> tuple[list, list, list]:
    if not isinstance(document, dict):
        raise ValueError(f"{source_id}: signalset root must be an object")
    ecus = document.get("ecu", [])
    commands = document.get("commands")
    if not isinstance(ecus, list) or not isinstance(commands, list):
        raise ValueError(f"{source_id}: ecu and commands must be arrays")
    normalized_ecus = []
    for ordinal, ecu in enumerate(ecus):
        if not isinstance(ecu, dict):
            raise ValueError(f"{source_id}: invalid ECU row")
        header = validate_hex(ecu.get("hdr"), "ECU header", 3)
        normalized_ecus.append((ordinal, header, str(ecu.get("type") or ""), ecu))

    normalized_commands = []
    normalized_signals = []
    for command_ordinal, command in enumerate(commands):
        if not isinstance(command, dict):
            raise ValueError(f"{source_id}: command must be an object")
        header = validate_hex(command.get("hdr"), "command ECU header", min_len=3, max_len=4)
        command_map = command.get("cmd")
        if not isinstance(command_map, dict) or len(command_map) != 1:
            raise ValueError(f"{source_id}: each command must have exactly one service entry")
        service_id = validate_hex(next(iter(command_map.keys())), "service identifier", 2)
        if service_id != "22":
            raise ValueError(f"{source_id}: non-read-only service {service_id} is not accepted in this reference pack")
        data_identifier = validate_hex(next(iter(command_map.values())), "data identifier")
        frequency = command.get("freq")
        if not isinstance(frequency, (int, float)) or isinstance(frequency, bool) or not math.isfinite(float(frequency)) or float(frequency) <= 0:
            raise ValueError(f"{source_id}: invalid command frequency")
        signals = command.get("signals")
        if not isinstance(signals, list) or not signals:
            raise ValueError(f"{source_id}: command has no signals")
        finite_json(command, f"{source_id} command {command_ordinal}")
        normalized_commands.append({
            "ordinal": command_ordinal,
            "ecu_header": header,
            "response_header": validate_hex(command.get("rax"), "response header", min_len=3, max_len=8) if command.get("rax") else None,
            "fcm1": 1 if command.get("fcm1") is True else 0,
            "debug_flag": 1 if command.get("dbg") is True else 0,
            "service_id": service_id,
            "data_identifier": data_identifier,
            "frequency": float(frequency),
            "filter_json": canonical_json(command.get("filter")) if command.get("filter") is not None else None,
            "dbgfilter_json": canonical_json(command.get("dbgfilter")) if command.get("dbgfilter") is not None else None,
            "raw_json": canonical_json(command),
            "record_sha256": sha256(canonical_json(command).encode("utf-8")),
        })
        for signal_ordinal, signal in enumerate(signals):
            if not isinstance(signal, dict):
                raise ValueError(f"{source_id}: signal must be an object")
            signal_key = str(signal.get("id") or "").strip()
            name = str(signal.get("name") or "").strip()
            fmt = signal.get("fmt")
            if not signal_key or len(signal_key) > 160 or not name or len(name) > 300 or not isinstance(fmt, dict):
                raise ValueError(f"{source_id}: invalid signal identity or format")
            bit_length = fmt.get("len")
            if not isinstance(bit_length, int) or isinstance(bit_length, bool) or bit_length <= 0 or bit_length > 512:
                raise ValueError(f"{source_id}: invalid signal bit length for {signal_key}")
            finite_json(signal, f"{source_id} signal {signal_key}")
            raw_signal = canonical_json(signal)
            normalized_signals.append({
                "command_ordinal": command_ordinal,
                "signal_ordinal": signal_ordinal,
                "signal_key": signal_key,
                "name": name,
                "description": str(signal.get("description") or ""),
                "path": str(signal.get("path") or ""),
                "unit": str(fmt.get("unit") or ""),
                "format_json": canonical_json(fmt),
                "suggested_metric": str(signal.get("suggestedMetric") or ""),
                "raw_json": raw_signal,
                "record_sha256": sha256(raw_signal.encode("utf-8")),
            })
    return normalized_ecus, normalized_commands, normalized_signals


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript("""
    PRAGMA foreign_keys=ON;
    CREATE TABLE source_registry (
      source_id TEXT PRIMARY KEY,
      repository TEXT NOT NULL,
      repository_url TEXT NOT NULL,
      make_name TEXT NOT NULL,
      model_name TEXT NOT NULL,
      commit_sha TEXT NOT NULL,
      commit_date TEXT NOT NULL,
      license_id TEXT NOT NULL CHECK (license_id='CC-BY-SA-4.0'),
      license_url TEXT NOT NULL,
      license_sha256 TEXT NOT NULL,
      signalset_sha256 TEXT NOT NULL,
      generations_sha256 TEXT NOT NULL,
      readme_sha256 TEXT NOT NULL,
      market_scope TEXT NOT NULL CHECK (market_scope='UNKNOWN'),
      applicability_precision TEXT NOT NULL CHECK (applicability_precision='vehicle_model_candidate'),
      verification_status TEXT NOT NULL CHECK (verification_status='unverified_community_candidate'),
      share_alike_required INTEGER NOT NULL CHECK (share_alike_required=1),
      execution_allowed INTEGER NOT NULL CHECK (execution_allowed=0),
      attribution TEXT NOT NULL
    );
    CREATE TABLE source_files (
      source_id TEXT NOT NULL REFERENCES source_registry(source_id),
      relative_path TEXT NOT NULL,
      sha256 TEXT NOT NULL,
      byte_count INTEGER NOT NULL,
      PRIMARY KEY(source_id, relative_path)
    );
    CREATE TABLE generation_candidates (
      generation_id INTEGER PRIMARY KEY,
      source_id TEXT NOT NULL REFERENCES source_registry(source_id),
      generation_name TEXT NOT NULL,
      year_start INTEGER,
      year_end INTEGER,
      reference_url TEXT NOT NULL,
      market_scope TEXT NOT NULL CHECK (market_scope='UNKNOWN'),
      applicability_precision TEXT NOT NULL CHECK (applicability_precision='vehicle_generation_candidate'),
      verification_status TEXT NOT NULL CHECK (verification_status='unverified_community_candidate'),
      raw_line TEXT NOT NULL
    );
    CREATE TABLE ecu_candidates (
      ecu_id INTEGER PRIMARY KEY,
      source_id TEXT NOT NULL REFERENCES source_registry(source_id),
      ordinal INTEGER NOT NULL,
      header TEXT NOT NULL,
      ecu_type TEXT NOT NULL,
      raw_json TEXT NOT NULL,
      record_sha256 TEXT NOT NULL,
      market_scope TEXT NOT NULL CHECK (market_scope='UNKNOWN'),
      applicability_precision TEXT NOT NULL CHECK (applicability_precision='vehicle_model_candidate'),
      verification_status TEXT NOT NULL CHECK (verification_status='unverified_community_candidate'),
      UNIQUE(source_id, ordinal)
    );
    CREATE TABLE command_candidates (
      command_id INTEGER PRIMARY KEY,
      source_id TEXT NOT NULL REFERENCES source_registry(source_id),
      ordinal INTEGER NOT NULL,
      ecu_header TEXT NOT NULL,
      response_header TEXT,
      fcm1 INTEGER NOT NULL,
      debug_flag INTEGER NOT NULL,
      service_id TEXT NOT NULL CHECK (service_id='22'),
      data_identifier TEXT NOT NULL,
      frequency REAL NOT NULL CHECK (frequency > 0),
      filter_json TEXT,
      dbgfilter_json TEXT,
      raw_json TEXT NOT NULL,
      record_sha256 TEXT NOT NULL,
      market_scope TEXT NOT NULL CHECK (market_scope='UNKNOWN'),
      applicability_precision TEXT NOT NULL CHECK (applicability_precision='vehicle_model_candidate'),
      verification_status TEXT NOT NULL CHECK (verification_status='unverified_community_candidate'),
      execution_allowed INTEGER NOT NULL CHECK (execution_allowed=0),
      UNIQUE(source_id, ordinal)
    );
    CREATE TABLE signal_candidates (
      signal_id INTEGER PRIMARY KEY,
      command_id INTEGER NOT NULL REFERENCES command_candidates(command_id),
      source_id TEXT NOT NULL REFERENCES source_registry(source_id),
      ordinal INTEGER NOT NULL,
      signal_key TEXT NOT NULL,
      name TEXT NOT NULL,
      description TEXT NOT NULL,
      path TEXT NOT NULL,
      unit TEXT NOT NULL,
      format_json TEXT NOT NULL,
      suggested_metric TEXT NOT NULL,
      raw_json TEXT NOT NULL,
      record_sha256 TEXT NOT NULL,
      market_scope TEXT NOT NULL CHECK (market_scope='UNKNOWN'),
      applicability_precision TEXT NOT NULL CHECK (applicability_precision='vehicle_model_candidate'),
      verification_status TEXT NOT NULL CHECK (verification_status='unverified_community_candidate'),
      UNIQUE(command_id, ordinal)
    );
    CREATE TABLE build_info (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );
    CREATE INDEX idx_generation_model ON generation_candidates(source_id, year_start, year_end);
    CREATE INDEX idx_command_source_did ON command_candidates(source_id, data_identifier);
    CREATE INDEX idx_signal_key ON signal_candidates(signal_key);
    CREATE INDEX idx_signal_name ON signal_candidates(name);
    CREATE INDEX idx_signal_path ON signal_candidates(path);
    PRAGMA user_version=1;
    """)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Empty output directory for the research pack")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("license_id") != "CC-BY-SA-4.0":
        raise ValueError("Unsupported source manifest or license")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("No pinned sources in manifest")

    output = Path(args.output).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    upstream_root = output / "upstream"
    upstream_root.mkdir(parents=True, exist_ok=True)
    licenses_root = output / "LICENSES"
    licenses_root.mkdir(parents=True, exist_ok=True)

    all_downloaded = 0
    prepared = []
    for source in sources:
        repository = source["repository"]
        commit = source["commit_sha"]
        source_id = source["source_id"]
        files = {}
        for relative_path in SOURCE_PATHS:
            payload = fetch_pinned(repository, commit, relative_path)
            all_downloaded += len(payload)
            if all_downloaded > MAX_TOTAL_BYTES:
                raise ValueError("Total upstream download exceeded the configured limit")
            files[relative_path] = payload
        license_text = files["LICENSE"].decode("utf-8-sig")
        if "Attribution-ShareAlike 4.0 International" not in license_text:
            raise ValueError(f"{source_id}: upstream LICENSE is not CC BY-SA 4.0")
        signalset = json.loads(files["signalsets/v3/default.json"].decode("utf-8-sig"))
        ecus, commands, signals = validate_signalset(signalset, source_id)
        generations_text = files["generations.yaml"].decode("utf-8-sig")
        generations = parse_generation_candidates(generations_text, source.get("generation_reference_url", source["repository_url"]))
        if not commands and not generations:
            raise ValueError(f"{source_id}: no signal commands or generation candidates in pinned snapshot")
        source_files = {}
        source_root = upstream_root / source_id
        for relative_path, payload in files.items():
            destination = source_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            source_files[relative_path] = {
                "path": str(destination.relative_to(output)).replace("\\", "/"),
                "sha256": sha256(payload),
                "bytes": len(payload),
            }
        license_copy = licenses_root / f"{source_id}-LICENSE.txt"
        license_copy.write_bytes(files["LICENSE"])
        prepared.append({
            "source": source,
            "files": files,
            "source_files": source_files,
            "license_sha256": sha256(files["LICENSE"]),
            "signalset_sha256": sha256(files["signalsets/v3/default.json"]),
            "generations_sha256": sha256(files["generations.yaml"]),
            "readme_sha256": sha256(files["README.md"]),
            "license_copy": str(license_copy.relative_to(output)).replace("\\", "/"),
            "ecus": ecus,
            "commands": commands,
            "signals": signals,
            "generations": generations,
        })

    database_path = output / "vag-obdb-research.sqlite"
    temporary_path = output / "vag-obdb-research.sqlite.tmp"
    if temporary_path.exists():
        temporary_path.unlink()
    connection = sqlite3.connect(temporary_path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA synchronous=FULL")
    create_schema(connection)
    connection.execute("BEGIN IMMEDIATE")
    try:
        for item in prepared:
            source = item["source"]
            source_id = source["source_id"]
            attribution = f"OBDb community contributors; {source['repository']} at {source['commit_sha']}"
            connection.execute("""
              INSERT INTO source_registry VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                source_id, source["repository"], source["repository_url"], source["make"], source["model"],
                source["commit_sha"], source["commit_date"], "CC-BY-SA-4.0",
                manifest["license_url"], item["license_sha256"], item["signalset_sha256"],
                item["generations_sha256"], item["readme_sha256"], "UNKNOWN",
                "vehicle_model_candidate", "unverified_community_candidate", 1, 0, attribution,
            ))
            for relative_path, metadata in item["source_files"].items():
                connection.execute("INSERT INTO source_files VALUES(?,?,?,?)", (
                    source_id, relative_path, metadata["sha256"], metadata["bytes"],
                ))
            for generation in item["generations"]:
                connection.execute("""
                  INSERT INTO generation_candidates
                  (source_id,generation_name,year_start,year_end,reference_url,market_scope,applicability_precision,verification_status,raw_line)
                  VALUES(?,?,?,?,?,'UNKNOWN','vehicle_generation_candidate','unverified_community_candidate',?)
                """, (
                    source_id, generation["name"], generation["year_start"], generation["year_end"],
                    generation["reference_url"], generation["raw_line"],
                ))
            for ordinal, header, ecu_type, raw in item["ecus"]:
                raw_json = canonical_json(raw)
                connection.execute("""
                  INSERT INTO ecu_candidates
                  (source_id,ordinal,header,ecu_type,raw_json,record_sha256,market_scope,applicability_precision,verification_status)
                  VALUES(?,?,?,?,?,?,'UNKNOWN','vehicle_model_candidate','unverified_community_candidate')
                """, (source_id, ordinal, header, ecu_type, raw_json, sha256(raw_json.encode("utf-8"))))
            command_ids = {}
            for command in item["commands"]:
                cursor = connection.execute("""
                  INSERT INTO command_candidates
                  (source_id,ordinal,ecu_header,response_header,fcm1,debug_flag,service_id,data_identifier,frequency,filter_json,dbgfilter_json,raw_json,record_sha256,market_scope,applicability_precision,verification_status,execution_allowed)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'UNKNOWN','vehicle_model_candidate','unverified_community_candidate',0)
                """, (
                    source_id, command["ordinal"], command["ecu_header"], command["response_header"],
                    command["fcm1"], command["debug_flag"], command["service_id"], command["data_identifier"],
                    command["frequency"], command["filter_json"], command["dbgfilter_json"],
                    command["raw_json"], command["record_sha256"],
                ))
                command_ids[command["ordinal"]] = cursor.lastrowid
            for signal in item["signals"]:
                connection.execute("""
                  INSERT INTO signal_candidates
                  (command_id,source_id,ordinal,signal_key,name,description,path,unit,format_json,suggested_metric,raw_json,record_sha256,market_scope,applicability_precision,verification_status)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'UNKNOWN','vehicle_model_candidate','unverified_community_candidate')
                """, (
                    command_ids[signal["command_ordinal"]], source_id, signal["signal_ordinal"],
                    signal["signal_key"], signal["name"], signal["description"], signal["path"],
                    signal["unit"], signal["format_json"], signal["suggested_metric"],
                    signal["raw_json"], signal["record_sha256"],
                ))
        total_commands = connection.execute("SELECT count(*) FROM command_candidates").fetchone()[0]
        total_signals = connection.execute("SELECT count(*) FROM signal_candidates").fetchone()[0]
        total_ecus = connection.execute("SELECT count(*) FROM ecu_candidates").fetchone()[0]
        total_generations = connection.execute("SELECT count(*) FROM generation_candidates").fetchone()[0]
        for key, value in {
            "schema_version": "1",
            "dataset_id": manifest["dataset_id"],
            "license_id": manifest["license_id"],
            "market_scope": "UNKNOWN",
            "verification_status": "unverified_community_candidate",
            "execution_allowed": "false",
            "command_count": str(total_commands),
            "signal_count": str(total_signals),
            "ecu_candidate_count": str(total_ecus),
            "generation_candidate_count": str(total_generations),
        }.items():
            connection.execute("INSERT INTO build_info VALUES(?,?)", (key, value))
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        raise
    connection.close()
    check = sqlite3.connect(temporary_path)
    integrity = check.execute("PRAGMA integrity_check").fetchone()[0]
    foreign_keys = check.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign_keys:
        check.close()
        raise RuntimeError(f"SQLite verification failed: integrity={integrity}, foreign_keys={foreign_keys[:5]}")
    check.close()
    os.replace(temporary_path, database_path)

    counts = {
        "sources": len(prepared),
        "generations": sum(len(item["generations"]) for item in prepared),
        "ecus": sum(len(item["ecus"]) for item in prepared),
        "commands": sum(len(item["commands"]) for item in prepared),
        "signals": sum(len(item["signals"]) for item in prepared),
    }
    source_manifest = {
        "schema_version": 1,
        "dataset_id": manifest["dataset_id"],
        "license_id": manifest["license_id"],
        "license_url": manifest["license_url"],
        "license_status": "declared_in_each_pinned_upstream_repository",
        "commercial_use_allowed": True,
        "display_allowed": True,
        "cache_allowed": True,
        "redistribution_allowed": True,
        "share_alike_required": True,
        "attribution_required": True,
        "attribution": manifest["attribution"],
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "database_file": database_path.name,
        "database_sha256": sha256(database_path.read_bytes()),
        "counts": counts,
        "sources": [],
        "limitations": [
            "Community-authored signal candidates only; technical correctness has not been independently verified on a vehicle.",
            "Market scope is UNKNOWN for every source.",
            "Model-level repository scope does not establish generation, engine, gearbox, PR-code, ECU-hardware or VIN applicability.",
            "filter and dbgfilter payloads are preserved verbatim and are not interpreted as fitment rules.",
            "Only UDS service 0x22 read-data identifiers are present; this pack is reference-only and never sends commands to a vehicle.",
            "No DTC definitions, repair procedures, wiring diagrams, pinouts, torque values, adaptations or service schedules are included.",
            "Generation labels and year ranges are source candidates; they are not linked to signal rows as confirmed applicability.",
            "The adapted SQLite database must remain available under CC BY-SA 4.0 with attribution; do not apply DRM or additional restrictions to redistributed copies."
        ],
    }
    for item in prepared:
        source = item["source"]
        source_manifest["sources"].append({
            "source_id": source["source_id"],
            "repository": source["repository"],
            "repository_url": source["repository_url"],
            "commit_sha": source["commit_sha"],
            "commit_date": source["commit_date"],
            "make": source["make"],
            "model": source["model"],
            "market_scope": "UNKNOWN",
            "applicability_precision": "vehicle_model_candidate",
            "verification_status": "unverified_community_candidate",
            "execution_allowed": False,
            "license_copy": item["license_copy"],
            "license_sha256": item["license_sha256"],
            "counts": {
                "generations": len(item["generations"]),
                "ecus": len(item["ecus"]),
                "commands": len(item["commands"]),
                "signals": len(item["signals"]),
            },
            "files": item["source_files"],
        })
    (output / "manifest.json").write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    attribution_lines = [
        "OBDb VAG community signal-set research pack",
        "License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).",
        "This is an adapted SQLite database. It is separately licensed under CC BY-SA 4.0.",
        "Attribution: OBDb community contributors; each repository, pinned commit, file hash and license copy is listed in manifest.json.",
        "No DRM or additional restriction is applied to the redistributed database.",
        "",
    ]
    for source in source_manifest["sources"]:
        attribution_lines.append(f"{source['make']} {source['model']}: {source['repository']} @ {source['commit_sha']}")
    (output / "ATTRIBUTION.txt").write_text("\n".join(attribution_lines) + "\n", encoding="utf-8")
    readme = """# OBDb VAG signal research pack

This folder contains a separate, read-only SQLite adaptation of six OBDb community signal-set repositories.

License: CC BY-SA 4.0. Commercial use is allowed under that license, subject to attribution and ShareAlike. The adapted database is distributed under CC BY-SA 4.0. Do not apply DRM or additional restrictions to copies of this database.

The SQLite file preserves pinned upstream commits, source file SHA-256 values, license copies, model labels, generation candidates, ECU headers, UDS 0x22 identifiers, signal formats, and the original filter/debug-filter JSON.

This is not factory service information. Market is UNKNOWN; exact generation, engine, gearbox, PR-code, ECU hardware, and VIN applicability are not established. All signal records are unverified community candidates. Filter fields are not interpreted. No command is executed by this pack.

The pack contains no DTC definitions, repair procedures, wiring diagrams, pinouts, torque specifications, adaptations, or service schedules. Always verify a signal definition on the actual vehicle with suitable equipment before relying on it.
"""
    (output / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({
        "status": "built",
        "database": str(database_path),
        "database_sha256": source_manifest["database_sha256"],
        "counts": counts,
        "license": "CC-BY-SA-4.0",
        "market_scope": "UNKNOWN",
        "verification_status": "unverified_community_candidate",
        "execution_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
