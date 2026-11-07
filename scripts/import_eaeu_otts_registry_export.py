#!/usr/bin/env python3
"""Fail-closed importer for an authorized EAEU TR TS 018/2011 registry XML export.

This tool never scrapes the portal and never writes into the production catalogue.
Persistent staging requires owner-reviewed written reuse rights and a matching
permission-evidence file. Every imported technical value remains an unverified
candidate until separate vehicle-specific review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_ID = "eaeu-otts-unified-register-public-portal"
SCHEMA_ID = "R.TR.TS.07.001"
SCHEMA_VERSION = "1.0.0"
EXPECTED_NAMESPACE = "urn:EEC:R:TR:TS:07:ConformityVehicleDocsRegistryDetails:v1.0.0"
EXPECTED_ROOT = "ConformityVehicleDocsRegistryDetails"
MAX_INPUT_BYTES = 100 * 1024 * 1024
DOCUMENT_TYPES = {"30": "OTTS", "35": "OTSH", "40": "SBKTS"}
STATUS_LABELS = {
    "1": "active",
    "2": "suspended",
    "3": "terminated",
    "4": "extended",
    "5": "resumed",
}
TRANSMISSION_UNIT_LABELS = {
    "05": "gearbox",
    "10": "transfer_case",
    "15": "final_drive",
    "20": "power_take_off",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_regular_file(path: str | Path, *, max_bytes: int | None = None) -> bytes:
    target = Path(path)
    try:
        info = target.lstat()
    except OSError as exc:
        raise ValueError(f"Cannot stat file {target}: {exc}") from exc
    if target.is_symlink() or not target.is_file():
        raise ValueError(f"Input must be a regular, non-symlink file: {target}")
    if max_bytes is not None and info.st_size > max_bytes:
        raise ValueError(f"Input exceeds the {max_bytes}-byte safety limit: {target}")
    try:
        return target.read_bytes()
    except OSError as exc:
        raise ValueError(f"Cannot read file {target}: {exc}") from exc


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _namespace(tag: str) -> str | None:
    if not isinstance(tag, str) or not tag.startswith("{"):
        return None
    return tag[1:].split("}", 1)[0]


def _validate_element_namespaces(root: ET.Element) -> None:
    unexpected: list[tuple[str, str | None]] = []
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        namespace = _namespace(element.tag)
        if namespace != EXPECTED_NAMESPACE:
            unexpected.append((_local_name(element.tag), namespace))
            if len(unexpected) >= 5:
                break
    if unexpected:
        details = ", ".join(
            f"{name!r} in {namespace!r}" for name, namespace in unexpected
        )
        raise ValueError(
            "Unexpected XML element namespace; every element must use "
            f"{EXPECTED_NAMESPACE!r}; found {details}"
        )


def _text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _direct_children(parent: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(parent) if _local_name(child.tag) == name]


def _first_direct(parent: ET.Element, name: str) -> ET.Element | None:
    return next(iter(_direct_children(parent, name)), None)


def _first_direct_text(parent: ET.Element, name: str) -> str | None:
    return _text(_first_direct(parent, name))


def _descendants(parent: ET.Element, name: str) -> list[ET.Element]:
    return [element for element in parent.iter() if element is not parent and _local_name(element.tag) == name]


def _first_descendant(parent: ET.Element, name: str) -> ET.Element | None:
    return next(iter(_descendants(parent, name)), None)


def _first_descendant_text(parent: ET.Element, name: str) -> str | None:
    return _text(_first_descendant(parent, name))


def _measure(parent: ET.Element, name: str) -> dict[str, str | None]:
    element = _first_descendant(parent, name)
    if element is None:
        return {"value": None, "unit_code": None}
    return {
        "value": _text(element),
        "unit_code": element.attrib.get("measurementUnitCode"),
    }


def _hash_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def _document_kind(record: ET.Element) -> tuple[str, str | None]:
    code = _first_direct_text(record, "ConformityDocKindCode")
    name = _first_direct_text(record, "ConformityDocKindName")
    if code:
        return code.strip(), name
    normalized = " ".join((name or "").lower().split())
    if "одобрение типа транспортного средства" in normalized:
        return "30", name
    if "одобрение типа шасси" in normalized:
        return "35", name
    if "свидетельство о безопасности конструкции транспортного средства" in normalized:
        return "40", name
    raise ValueError("Registry record has neither a recognized ConformityDocKindCode nor a recognized ConformityDocKindName")


def _parse_engine(element: ET.Element) -> dict[str, Any]:
    return {
        "component_make_name": _first_descendant_text(element, "VehicleComponentMakeName"),
        "component_model_code": _first_descendant_text(element, "VehicleComponentModelCode"),
        "component_text": _first_descendant_text(element, "VehicleComponentText"),
        "cylinder_quantity": _first_descendant_text(element, "EngineCylinderQuantity"),
        "cylinder_arrangement_text": _first_descendant_text(element, "EngineCylinderArrangementText"),
        "capacity": _measure(element, "EngineCapacityMeasure"),
        "compression_rate": _first_descendant_text(element, "EngineCompressionRate"),
        "max_power": _measure(element, "EngineMaxPowerMeasure"),
        "max_torque": _measure(element, "EngineMaxTorqueMeasure"),
        "code_namespace": "EAEU_TR_TS_018_2011_VehicleComponentModelCode_engine",
        "code_semantics": "manufacturer_assigned_engine_type_code_not_assumed_to_be_a_VAG_three_letter_code",
        "verification_status": "candidate_unverified",
    }


def _parse_transmission_unit(element: ET.Element) -> dict[str, Any]:
    unit_code = _first_descendant_text(element, "VehicleUnitKindCode")
    return {
        "unit_kind_code": unit_code,
        "unit_kind_label": TRANSMISSION_UNIT_LABELS.get(unit_code or "", "unknown"),
        "component_make_name": _first_descendant_text(element, "VehicleComponentMakeName"),
        "component_model_code": _first_descendant_text(element, "VehicleComponentModelCode"),
        "component_text": _first_descendant_text(element, "VehicleComponentText"),
        "gear_quantity": _first_descendant_text(element, "TransmissionUnitGearQuantity"),
        "code_namespace": "EAEU_TR_TS_018_2011_VehicleComponentModelCode_transmission_unit",
        "code_semantics": "manufacturer_assigned_transmission_unit_type_code_not_assumed_to_be_a_VAG_gearbox_code",
        "verification_status": "candidate_unverified",
    }


def _parse_variant(element: ET.Element) -> dict[str, Any]:
    engines = [_parse_engine(item) for item in _descendants(element, "EngineDetails")]
    transmissions = [_parse_transmission_unit(item) for item in _descendants(element, "TransmissionUnitDetails")]
    ecu_codes = []
    for item in _descendants(element, "ECUModelCode"):
        value = _text(item)
        if value and value not in ecu_codes:
            ecu_codes.append(value)

    engine_code_indexes = [index for index, engine in enumerate(engines) if engine.get("component_model_code")]
    gearbox_indexes = [
        index for index, unit in enumerate(transmissions)
        if unit.get("unit_kind_code") == "05" and unit.get("component_model_code")
    ]
    gearbox_unit_indexes = [index for index, unit in enumerate(transmissions) if unit.get("unit_kind_code") == "05"]

    variant_id = _first_direct_text(element, "VehicleTypeVariantId")
    pair_candidates = []
    if len(engines) == 1 and len(engine_code_indexes) == 1 and len(gearbox_unit_indexes) == 1 and len(gearbox_indexes) == 1:
        pair_candidates.append({
            "engine_index": engine_code_indexes[0],
            "transmission_index": gearbox_indexes[0],
            "evidence_rule": "single_engine_and_single_gearbox_code_nested_under_same_approval_variant_element",
            "applicability_precision": (
                "same_approval_variant_id_single_pair_candidate"
                if variant_id
                else "same_unlabelled_approval_variant_single_pair_candidate"
            ),
            "verification_status": "candidate_unverified",
        })

    variant = {
        "variant_id": variant_id,
        "eco_class_code": _first_direct_text(element, "VehicleEcoClassCode"),
        "chassis_design_code": _first_direct_text(element, "VehicleChassisDesignCode"),
        "engines": engines,
        "transmissions": transmissions,
        "ecu_codes": ecu_codes,
        "pair_candidates": pair_candidates,
        "applicability_precision": (
            "approval_variant_candidate"
            if variant_id
            else "approval_variant_unlabelled_candidate"
        ),
        "verification_status": "candidate_unverified",
    }
    variant["normalized_record_sha256"] = _hash_json(variant)
    return variant


def _parse_document(record: ET.Element) -> dict[str, Any]:
    kind_code, kind_name = _document_kind(record)
    if kind_code not in DOCUMENT_TYPES:
        raise ValueError(f"Unsupported EAEU conformity document kind code: {kind_code}")
    if kind_code == "40":
        return {"_skip": "SBKTS"}

    issuing_country_code = (_first_direct_text(record, "UnifiedCountryCode") or "").upper()
    document_id = _first_direct_text(record, "DocId")
    start_date = _first_direct_text(record, "DocStartDate")
    if not re.fullmatch(r"[A-Z]{2}", issuing_country_code):
        raise ValueError("EAEU OTTS/OTSH record is missing a valid two-letter issuing-country code")
    if not document_id:
        raise ValueError("EAEU OTTS/OTSH record is missing DocId")
    if not start_date or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", start_date):
        raise ValueError("EAEU OTTS/OTSH record is missing a valid DocStartDate")

    type_element = _first_direct(record, "VehicleTypeDetails")
    variant_elements = _direct_children(record, "VehicleVariantDetails")
    if not variant_elements:
        variant_elements = _descendants(record, "VehicleVariantDetails")
    if not variant_elements:
        raise ValueError(f"EAEU document {document_id} contains no VehicleVariantDetails")
    # Decision No. 88, table 6, rule 34: when a document contains more than
    # one vehicle modification/variant, each variant identifier is required.
    if len(variant_elements) > 1 and any(
        not _first_direct_text(item, "VehicleTypeVariantId")
        for item in variant_elements
    ):
        raise ValueError(
            f"EAEU document {document_id} has multiple variants but at least one "
            "VehicleTypeVariantId is missing (Decision No. 88, table 6, rule 34)"
        )
    variants = [_parse_variant(item) for item in variant_elements]

    status_element = _first_direct(record, "ConformityDocStatusDetails")

    vehicle_type = {
        "make_name": _first_descendant_text(type_element, "VehicleMakeName") if type_element is not None else None,
        "make_code": _first_descendant_text(type_element, "VehicleMakeCode") if type_element is not None else None,
        "commercial_name": _first_descendant_text(type_element, "VehicleCommercialName") if type_element is not None else None,
        "type_id": _first_descendant_text(type_element, "VehicleTypeId") if type_element is not None else None,
        "technical_category_code": _first_descendant_text(type_element, "VehicleTechCategoryCode") if type_element is not None else None,
    }
    status_code = _first_descendant_text(status_element, "DocStatusCode") if status_element is not None else None

    document = {
        "issuing_country_code": issuing_country_code,
        "market_scope": ["EAEU"],
        "document_id": document_id,
        "document_kind_code": kind_code,
        "document_type": DOCUMENT_TYPES[kind_code],
        "document_kind_name": kind_name,
        "document_creation_date": _first_direct_text(record, "DocCreationDate"),
        "document_start_date": start_date,
        "document_validity_date": _first_direct_text(record, "DocValidityDate"),
        "status_code": status_code,
        "status_label": STATUS_LABELS.get(status_code or "", "unknown_or_not_provided") if status_element is not None else "not_provided",
        "vehicle_type": vehicle_type,
        "model_year": None,
        "variants": variants,
        "applicability_precision": (
            "approval_variant_candidate"
            if any(item.get("variant_id") for item in variants)
            else "approval_document_candidate"
        ),
        "verification_status": "candidate_unverified",
    }
    document["normalized_record_sha256"] = _hash_json(document)
    return document


def parse_registry_export(raw: bytes) -> dict[str, Any]:
    if not raw:
        raise ValueError("EAEU registry export is empty")
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"EAEU registry export exceeds {MAX_INPUT_BYTES} bytes")
    # XML markup is ASCII-compatible in UTF-8/16/32; strip interleaved NUL
    # bytes so DTD/entity declarations cannot bypass the fail-closed scan.
    upper = raw.upper().replace(b"\x00", b"")
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("DTD/entity declarations are not accepted")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError(f"EAEU registry export is not well-formed XML: {exc}") from exc

    if _local_name(root.tag) != EXPECTED_ROOT or _namespace(root.tag) != EXPECTED_NAMESPACE:
        raise ValueError(
            f"Expected {EXPECTED_ROOT} in namespace {EXPECTED_NAMESPACE}; "
            f"received {_local_name(root.tag)} in {_namespace(root.tag)}"
        )
    _validate_element_namespaces(root)

    header = {
        "document_code": _first_descendant_text(root, "EDocCode"),
        "message_created_at": _first_descendant_text(root, "EDocDateTime"),
        "language_code": _first_descendant_text(root, "LanguageCode"),
    }
    records = [item for item in root.iter() if _local_name(item.tag) == "VehicleConformityDocDetails"]
    if not records:
        raise ValueError("EAEU registry export contains no VehicleConformityDocDetails records")

    documents = []
    skipped_sbkts = 0
    for record in records:
        parsed = _parse_document(record)
        if parsed.get("_skip") == "SBKTS":
            skipped_sbkts += 1
            continue
        documents.append(parsed)

    return {
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "message_header": header,
        "documents": documents,
        "skipped_sbkts": skipped_sbkts,
        "counts": {
            "documents": len(documents),
            "variants": sum(len(doc["variants"]) for doc in documents),
            "engine_candidates": sum(len(v["engines"]) for doc in documents for v in doc["variants"]),
            "transmission_unit_candidates": sum(len(v["transmissions"]) for doc in documents for v in doc["variants"]),
            "ecu_candidates": sum(len(v["ecu_codes"]) for doc in documents for v in doc["variants"]),
            "same_variant_pair_candidates": sum(len(v["pair_candidates"]) for doc in documents for v in doc["variants"]),
            "skipped_sbkts": skipped_sbkts,
        },
    }


def load_source_entry(source_manifest_path: str | Path, source_id: str = SOURCE_ID) -> tuple[bytes, dict[str, Any]]:
    raw = _read_regular_file(source_manifest_path, max_bytes=20 * 1024 * 1024)
    try:
        manifest = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Source register is not valid UTF-8 JSON: {exc}") from exc
    sources = manifest.get("sources") if isinstance(manifest, dict) else None
    if not isinstance(sources, list):
        raise ValueError("Source register must contain a sources array")
    matches = [item for item in sources if isinstance(item, dict) and item.get("source_id") == source_id]
    if len(matches) != 1:
        raise ValueError(f"Source register must contain exactly one {source_id} entry")
    return raw, matches[0]


def verify_persistent_import_rights(source: dict[str, Any], evidence_path: str | Path) -> str:
    rights = source.get("rights") if isinstance(source.get("rights"), dict) else {}
    if rights.get("permission_status") != "approved_for_offline_distribution":
        raise ValueError("Persistent EAEU data caching is blocked: source permission_status is not approved_for_offline_distribution")
    if rights.get("review_status") != "approved_by_owner":
        raise ValueError("Persistent EAEU data caching is blocked: owner rights review is not approved")
    required_flags = (
        "commercial_use_allowed",
        "bulk_reuse_allowed",
        "offline_cache_allowed",
        "display_and_redistribution_allowed",
    )
    missing = [flag for flag in required_flags if rights.get(flag) is not True]
    if missing:
        raise ValueError("Persistent EAEU data caching is blocked: rights flags are not explicitly true: " + ", ".join(missing))

    evidence = rights.get("permission_evidence")
    if not isinstance(evidence, dict):
        raise ValueError("Persistent EAEU data caching requires a permission_evidence object")
    evidence_url = evidence.get("url")
    expected_hash = evidence.get("sha256")
    if not isinstance(evidence_url, str) or not evidence_url.startswith("https://"):
        raise ValueError("Permission evidence must have an HTTPS URL")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", expected_hash):
        raise ValueError("Permission evidence must have a valid SHA-256")
    if not rights.get("reviewed_at") or not rights.get("approval_reference"):
        raise ValueError("Permission evidence must include reviewed_at and approval_reference")

    evidence_bytes = _read_regular_file(evidence_path, max_bytes=50 * 1024 * 1024)
    actual_hash = sha256_bytes(evidence_bytes)
    if actual_hash.lower() != expected_hash.lower():
        raise ValueError("Permission evidence SHA-256 does not match the source register")
    return actual_hash


def _create_database_schema(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE import_run (
            id INTEGER PRIMARY KEY,
            source_id TEXT NOT NULL,
            source_revision TEXT NOT NULL,
            source_url TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            schema_id TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            input_sha256 TEXT NOT NULL,
            source_manifest_sha256 TEXT NOT NULL,
            permission_evidence_sha256 TEXT NOT NULL,
            rights_status TEXT NOT NULL,
            import_mode TEXT NOT NULL CHECK (import_mode = 'staging_only'),
            distribution_eligible INTEGER NOT NULL CHECK (distribution_eligible = 0)
        );
        CREATE TABLE approval_document (
            id INTEGER PRIMARY KEY,
            import_run_id INTEGER NOT NULL REFERENCES import_run(id),
            issuing_country_code TEXT NOT NULL,
            market_scope_json TEXT NOT NULL,
            document_id TEXT NOT NULL,
            document_kind_code TEXT NOT NULL,
            document_type TEXT NOT NULL,
            document_creation_date TEXT,
            document_start_date TEXT NOT NULL,
            document_validity_date TEXT,
            status_code TEXT,
            status_label TEXT NOT NULL,
            vehicle_make_name TEXT,
            vehicle_make_code TEXT,
            commercial_name TEXT,
            vehicle_type_id TEXT,
            technical_category_code TEXT,
            model_year TEXT,
            normalized_record_sha256 TEXT NOT NULL,
            applicability_precision TEXT NOT NULL,
            verification_status TEXT NOT NULL CHECK (verification_status = 'candidate_unverified'),
            UNIQUE(issuing_country_code, document_id, document_kind_code, normalized_record_sha256)
        );
        CREATE TABLE vehicle_variant (
            id INTEGER PRIMARY KEY,
            approval_document_id INTEGER NOT NULL REFERENCES approval_document(id),
            variant_id TEXT,
            eco_class_code TEXT,
            chassis_design_code TEXT,
            normalized_record_sha256 TEXT NOT NULL,
            applicability_precision TEXT NOT NULL,
            verification_status TEXT NOT NULL CHECK (verification_status = 'candidate_unverified')
        );
        CREATE TABLE engine_candidate (
            id INTEGER PRIMARY KEY,
            vehicle_variant_id INTEGER NOT NULL REFERENCES vehicle_variant(id),
            component_make_name TEXT,
            component_model_code TEXT,
            code_namespace TEXT NOT NULL,
            code_semantics TEXT NOT NULL,
            component_text TEXT,
            cylinder_quantity TEXT,
            cylinder_arrangement_text TEXT,
            capacity_value TEXT,
            capacity_unit_code TEXT,
            compression_rate TEXT,
            max_power_value TEXT,
            max_power_unit_code TEXT,
            max_torque_value TEXT,
            max_torque_unit_code TEXT,
            verification_status TEXT NOT NULL CHECK (verification_status = 'candidate_unverified')
        );
        CREATE TABLE transmission_candidate (
            id INTEGER PRIMARY KEY,
            vehicle_variant_id INTEGER NOT NULL REFERENCES vehicle_variant(id),
            unit_kind_code TEXT,
            unit_kind_label TEXT NOT NULL,
            component_make_name TEXT,
            component_model_code TEXT,
            code_namespace TEXT NOT NULL,
            code_semantics TEXT NOT NULL,
            component_text TEXT,
            gear_quantity TEXT,
            verification_status TEXT NOT NULL CHECK (verification_status = 'candidate_unverified')
        );
        CREATE TABLE ecu_candidate (
            id INTEGER PRIMARY KEY,
            vehicle_variant_id INTEGER NOT NULL REFERENCES vehicle_variant(id),
            ecu_model_code TEXT NOT NULL,
            code_namespace TEXT NOT NULL,
            verification_status TEXT NOT NULL CHECK (verification_status = 'candidate_unverified')
        );
        CREATE TABLE powertrain_pair_candidate (
            id INTEGER PRIMARY KEY,
            vehicle_variant_id INTEGER NOT NULL REFERENCES vehicle_variant(id),
            engine_candidate_id INTEGER NOT NULL REFERENCES engine_candidate(id),
            transmission_candidate_id INTEGER NOT NULL REFERENCES transmission_candidate(id),
            evidence_rule TEXT NOT NULL,
            applicability_precision TEXT NOT NULL,
            verification_status TEXT NOT NULL CHECK (verification_status = 'candidate_unverified')
        );
        CREATE TABLE source_provenance (
            id INTEGER PRIMARY KEY,
            approval_document_id INTEGER NOT NULL REFERENCES approval_document(id),
            source_id TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_revision TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            market_scope_json TEXT NOT NULL,
            input_sha256 TEXT NOT NULL,
            normalized_record_sha256 TEXT NOT NULL,
            schema_id TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            rights_status TEXT NOT NULL,
            permission_evidence_sha256 TEXT NOT NULL
        );
        CREATE INDEX idx_approval_document_make_model
            ON approval_document(vehicle_make_name, commercial_name, vehicle_type_id);
        CREATE INDEX idx_engine_candidate_code
            ON engine_candidate(component_model_code);
        CREATE INDEX idx_transmission_candidate_code
            ON transmission_candidate(component_model_code);
    """)
    connection.execute("PRAGMA user_version = 1")
    connection.execute("PRAGMA application_id = 1448367186")


def write_staging_database(
    parsed: dict[str, Any],
    *,
    output_path: str | Path,
    source: dict[str, Any],
    source_manifest_sha256: str,
    input_sha256: str,
    retrieved_at: str,
    permission_evidence_sha256: str,
) -> dict[str, Any]:
    output = Path(output_path).absolute()
    sidecar = output.with_suffix(output.suffix + ".manifest.json")
    if output.exists() or output.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise FileExistsError("Refusing to overwrite an existing EAEU staging database or sidecar manifest")
    if not parsed["documents"]:
        raise ValueError("No OTTS/OTSH records are available for persistent staging")

    output.parent.mkdir(parents=True, exist_ok=True)
    db_fd, db_temp_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".staging", dir=output.parent)
    os.close(db_fd)
    side_fd, side_temp_name = tempfile.mkstemp(prefix=f".{sidecar.name}.", suffix=".staging", dir=output.parent)
    os.close(side_fd)
    db_temp = Path(db_temp_name)
    side_temp = Path(side_temp_name)
    installed_db = False

    source_id = source["source_id"]
    source_url = source.get("url") or source.get("source_url")
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        raise ValueError("EAEU source register entry must contain an HTTPS source URL")
    source_revision = source.get("source_revision") or f"Decision 88 / {SCHEMA_ID} v{SCHEMA_VERSION}"
    market_scope = source.get("market_scope") or ["EAEU"]
    rights_status = "owner_attested_not_independently_verified"

    counts = {
        "documents": 0,
        "variants": 0,
        "engine_candidates": 0,
        "transmission_unit_candidates": 0,
        "ecu_candidates": 0,
        "same_variant_pair_candidates": 0,
    }

    try:
        connection = sqlite3.connect(db_temp)
        try:
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.execute("PRAGMA synchronous = FULL")
            _create_database_schema(connection)
            connection.execute(
                """INSERT INTO import_run (
                    id, source_id, source_revision, source_url, retrieved_at,
                    schema_id, schema_version, input_sha256, source_manifest_sha256,
                    permission_evidence_sha256, rights_status, import_mode, distribution_eligible
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'staging_only', 0)""",
                (
                    source_id, source_revision, source_url, retrieved_at,
                    SCHEMA_ID, SCHEMA_VERSION, input_sha256, source_manifest_sha256,
                    permission_evidence_sha256, rights_status,
                ),
            )

            for document in parsed["documents"]:
                vehicle_type = document["vehicle_type"]
                cursor = connection.execute(
                    """INSERT INTO approval_document (
                        import_run_id, issuing_country_code, market_scope_json, document_id,
                        document_kind_code, document_type, document_creation_date,
                        document_start_date, document_validity_date, status_code, status_label,
                        vehicle_make_name, vehicle_make_code, commercial_name, vehicle_type_id,
                        technical_category_code, model_year, normalized_record_sha256,
                        applicability_precision, verification_status
                    ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate_unverified')""",
                    (
                        document["issuing_country_code"],
                        json.dumps(document["market_scope"], ensure_ascii=False),
                        document["document_id"],
                        document["document_kind_code"],
                        document["document_type"],
                        document["document_creation_date"],
                        document["document_start_date"],
                        document["document_validity_date"],
                        document["status_code"],
                        document["status_label"],
                        vehicle_type["make_name"],
                        vehicle_type["make_code"],
                        vehicle_type["commercial_name"],
                        vehicle_type["type_id"],
                        vehicle_type["technical_category_code"],
                        document["model_year"],
                        document["normalized_record_sha256"],
                        document["applicability_precision"],
                    ),
                )
                approval_id = int(cursor.lastrowid)
                counts["documents"] += 1

                connection.execute(
                    """INSERT INTO source_provenance (
                        approval_document_id, source_id, source_url, source_revision,
                        retrieved_at, market_scope_json, input_sha256,
                        normalized_record_sha256, schema_id, schema_version,
                        rights_status, permission_evidence_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        approval_id, source_id, source_url, source_revision,
                        retrieved_at, json.dumps(document["market_scope"], ensure_ascii=False),
                        input_sha256, document["normalized_record_sha256"],
                        SCHEMA_ID, SCHEMA_VERSION, rights_status, permission_evidence_sha256,
                    ),
                )

                for variant in document["variants"]:
                    variant_cursor = connection.execute(
                        """INSERT INTO vehicle_variant (
                            approval_document_id, variant_id, eco_class_code, chassis_design_code,
                            normalized_record_sha256, applicability_precision, verification_status
                        ) VALUES (?, ?, ?, ?, ?, ?, 'candidate_unverified')""",
                        (
                            approval_id, variant["variant_id"], variant["eco_class_code"],
                            variant["chassis_design_code"], variant["normalized_record_sha256"],
                            variant["applicability_precision"],
                        ),
                    )
                    variant_db_id = int(variant_cursor.lastrowid)
                    counts["variants"] += 1

                    engine_db_ids = []
                    for engine in variant["engines"]:
                        engine_cursor = connection.execute(
                            """INSERT INTO engine_candidate (
                                vehicle_variant_id, component_make_name, component_model_code,
                                code_namespace, code_semantics, component_text, cylinder_quantity,
                                cylinder_arrangement_text, capacity_value, capacity_unit_code,
                                compression_rate, max_power_value, max_power_unit_code,
                                max_torque_value, max_torque_unit_code, verification_status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate_unverified')""",
                            (
                                variant_db_id, engine["component_make_name"], engine["component_model_code"],
                                engine["code_namespace"], engine["code_semantics"], engine["component_text"],
                                engine["cylinder_quantity"], engine["cylinder_arrangement_text"],
                                engine["capacity"]["value"], engine["capacity"]["unit_code"],
                                engine["compression_rate"], engine["max_power"]["value"],
                                engine["max_power"]["unit_code"], engine["max_torque"]["value"],
                                engine["max_torque"]["unit_code"],
                            ),
                        )
                        engine_db_ids.append(int(engine_cursor.lastrowid))
                        counts["engine_candidates"] += 1

                    transmission_db_ids = []
                    for unit in variant["transmissions"]:
                        transmission_cursor = connection.execute(
                            """INSERT INTO transmission_candidate (
                                vehicle_variant_id, unit_kind_code, unit_kind_label,
                                component_make_name, component_model_code, code_namespace,
                                code_semantics, component_text, gear_quantity, verification_status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'candidate_unverified')""",
                            (
                                variant_db_id, unit["unit_kind_code"], unit["unit_kind_label"],
                                unit["component_make_name"], unit["component_model_code"],
                                unit["code_namespace"], unit["code_semantics"],
                                unit["component_text"], unit["gear_quantity"],
                            ),
                        )
                        transmission_db_ids.append(int(transmission_cursor.lastrowid))
                        counts["transmission_unit_candidates"] += 1

                    for ecu_code in variant["ecu_codes"]:
                        connection.execute(
                            """INSERT INTO ecu_candidate (
                                vehicle_variant_id, ecu_model_code, code_namespace, verification_status
                            ) VALUES (?, ?, 'EAEU_TR_TS_018_2011_ECUModelCode', 'candidate_unverified')""",
                            (variant_db_id, ecu_code),
                        )
                        counts["ecu_candidates"] += 1

                    for pair in variant["pair_candidates"]:
                        connection.execute(
                            """INSERT INTO powertrain_pair_candidate (
                                vehicle_variant_id, engine_candidate_id, transmission_candidate_id,
                                evidence_rule, applicability_precision, verification_status
                            ) VALUES (?, ?, ?, ?, ?, 'candidate_unverified')""",
                            (
                                variant_db_id,
                                engine_db_ids[pair["engine_index"]],
                                transmission_db_ids[pair["transmission_index"]],
                                pair["evidence_rule"],
                                pair["applicability_precision"],
                            ),
                        )
                        counts["same_variant_pair_candidates"] += 1

            connection.commit()
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
            if integrity != "ok" or foreign_key_errors:
                raise ValueError(f"Staging SQLite validation failed: integrity={integrity}, foreign_keys={foreign_key_errors[:5]}")
        finally:
            connection.close()

        database_sha256 = sha256_bytes(db_temp.read_bytes())
        sidecar_payload = {
            "schema_version": 1,
            "import_mode": "staging_only",
            "source_id": source_id,
            "source_url": source_url,
            "source_revision": source_revision,
            "market_scope": market_scope,
            "registry_schema": {"id": SCHEMA_ID, "version": SCHEMA_VERSION, "namespace": EXPECTED_NAMESPACE},
            "retrieved_at": retrieved_at,
            "input_sha256": input_sha256,
            "source_manifest_sha256": source_manifest_sha256,
            "permission_evidence_sha256": permission_evidence_sha256,
            "rights_status": rights_status,
            "distribution_eligible": False,
            "verification_status": "candidate_unverified",
            "counts": counts,
            "database_sha256": database_sha256,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        side_temp.write_text(json.dumps(sidecar_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(db_temp, output)
        installed_db = True
        os.replace(side_temp, sidecar)
        return {
            "status": "staging_created",
            "database": str(output),
            "sidecar_manifest": str(sidecar),
            "database_sha256": database_sha256,
            "rights_status": rights_status,
            "distribution_eligible": False,
            "counts": counts,
        }
    except Exception:
        if installed_db:
            try:
                output.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    finally:
        for temporary in (db_temp, side_temp):
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def import_export(
    *,
    input_path: str | Path,
    source_manifest_path: str | Path,
    retrieved_at: str,
    validate_only: bool = False,
    output_path: str | Path | None = None,
    permission_evidence_path: str | Path | None = None,
    source_id: str = SOURCE_ID,
) -> dict[str, Any]:
    try:
        parsed_time = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("retrieved_at must be an ISO-8601 timestamp with timezone") from exc
    if parsed_time.tzinfo is None:
        raise ValueError("retrieved_at must include a timezone")

    input_raw = _read_regular_file(input_path, max_bytes=MAX_INPUT_BYTES)
    manifest_raw, source = load_source_entry(source_manifest_path, source_id)
    parsed = parse_registry_export(input_raw)
    summary = {
        "status": "validated_only" if validate_only else "parsed",
        "source_id": source_id,
        "source_revision": source.get("source_revision") or f"Decision 88 / {SCHEMA_ID} v{SCHEMA_VERSION}",
        "retrieved_at": retrieved_at,
        "input_sha256": sha256_bytes(input_raw),
        "source_manifest_sha256": sha256_bytes(manifest_raw),
        "counts": parsed["counts"],
        "distribution_eligible": False,
    }
    if validate_only:
        return summary
    if output_path is None:
        raise ValueError("output_path is required unless validate_only is true")
    if permission_evidence_path is None:
        raise ValueError("permission_evidence_path is required for persistent offline caching")
    permission_sha = verify_persistent_import_rights(source, permission_evidence_path)
    created = write_staging_database(
        parsed,
        output_path=output_path,
        source=source,
        source_manifest_sha256=sha256_bytes(manifest_raw),
        input_sha256=sha256_bytes(input_raw),
        retrieved_at=retrieved_at,
        permission_evidence_sha256=permission_sha,
    )
    summary.update(created)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--source-manifest", required=True, type=Path)
    parser.add_argument("--retrieved-at", required=True, help="ISO-8601 timestamp including timezone")
    parser.add_argument("--source-id", default=SOURCE_ID)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--permission-evidence", type=Path)
    args = parser.parse_args(argv)

    if args.validate_only and (args.output or args.permission_evidence):
        parser.error("--validate-only cannot be combined with --output or --permission-evidence")
    if not args.validate_only and (args.output is None or args.permission_evidence is None):
        parser.error("persistent staging requires both --output and --permission-evidence; otherwise use --validate-only")

    try:
        result = import_export(
            input_path=args.input,
            source_manifest_path=args.source_manifest,
            retrieved_at=args.retrieved_at,
            validate_only=args.validate_only,
            output_path=args.output,
            permission_evidence_path=args.permission_evidence,
            source_id=args.source_id,
        )
    except Exception as exc:
        print(f"eaeu-otts-import-error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
