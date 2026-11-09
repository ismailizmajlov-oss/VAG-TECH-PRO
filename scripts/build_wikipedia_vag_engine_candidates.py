#!/usr/bin/env python3
"""Build a separately licensed, candidate-only Wikipedia VAG engine-code research pack."""
from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SOURCE_ID = "wikipedia-vag-engine-code-lists-cc-by-sa-4-0"
PACK_ID = "wikipedia-vag-engine-code-candidates-cc-by-sa-4-0"
LICENSE_ID = "CC-BY-SA-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "VAG-TECH-PRO research-pack builder/0.1 (https://github.com/ismailizmajlov-oss/VAG-TECH-PRO)"
EXCLUDED = {
    "EA111", "EA113", "EA189", "EA211", "EA288", "EA390", "EA395", "EA397",
    "EA824", "EA825", "EA827", "EA837", "EA838", "EA839", "EA855", "EA888", "EA897",
    "TDI", "TSI", "FSI", "MPI", "GDI", "SPI", "SDI", "PD", "CR", "SOHC", "DOHC",
    "R2", "R3", "R4", "R5", "R6", "V2", "V4", "V5", "V6", "V8", "V10", "V12",
    "W8", "W12", "W16", "VAG", "VW", "AUDI", "SEAT", "SKODA", "CUPRA",
    "ID", "CC", "PS", "KW", "NM", "BHP", "HP", "RPM", "DIN", "EGR", "ECU",
    "OBD", "EEC", "SI", "RON", "ROZ", "AKI", "PDI", "DSG", "CVT", "AT", "MT",
    "FWD", "RWD", "AWD", "4WD", "4MOTION", "QUATTRO", "VVT",
    "EU0", "EU1", "EU2", "EU3", "EU4", "EU5", "EU6", "EU7", "EU8", "EU9", "USA", "US", "CAN", "BRA",
}
CODE_RE = re.compile(r"(?<![A-Z0-9])[A-Z0-9]{2,5}(?![A-Z0-9])")
DECADE_RE = re.compile(r"^(?:19|20)\d{2}S$", re.IGNORECASE)
DISPLACEMENT_CODE_RE = re.compile(r"^\s*\d+(?:[.,]\d+)?(?:\s+[A-Za-z0-9]+){0,3}\s*:\s*(.+)$")
ID_CODE_VALUE_RE = re.compile(r"\b(?:engine\s+)?ID\s+codes?\s*:\s*(.+)$", re.IGNORECASE)
LABEL_RE = re.compile(
    r"\b(?:engine\s+(?:id|identification)\s+codes?|engine\s+codes?|(?:id|identification)\s+codes?)\b",
    re.IGNORECASE,
)
PAGES = {
    "List of Volkswagen Group petrol engines": 1383476161,
    "List of Volkswagen Group diesel engines": 1383504097,
    "List of discontinued Volkswagen Group petrol engines": 1381198237,
    "List of discontinued Volkswagen Group diesel engines": 1375791889,
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"\[\s*\d+\s*\]", " ", value)
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def is_engine_code_label(value: str) -> bool:
    return bool(LABEL_RE.search(clean_text(value)))


def is_explicit_engine_code_column(value: str) -> bool:
    text = clean_text(value)
    return bool(re.fullmatch(
        r"(?:(?:engine\s+)?(?:id|identification)\s+codes?|engine\s+codes?)(?:\s*\([^)]*\))?",
        text,
        re.IGNORECASE,
    ))


def extract_codes(value: str) -> list[str]:
    result: list[str] = []
    for match in CODE_RE.findall(clean_text(value).upper()):
        if match in EXCLUDED or match.isdigit() or DECADE_RE.fullmatch(match):
            continue
        if match not in result:
            result.append(match)
    return result


class EngineCodeHTMLParser(HTMLParser):
    """Extract only cells explicitly labelled as engine ID/code fields."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.heading = ""
        self.heading_buffer: list[str] | None = None
        self.table_depth = 0
        self.table_skip_stack: list[bool] = []
        self.table_skip_depth = 0
        self.engine_code_columns: set[int] = set()
        self.dt_buffer: list[str] | None = None
        self.dd_buffer: list[str] | None = None
        self.current_dt_label = ""
        self.table_has_id_code_header = False
        self.row: list[dict[str, str]] | None = None
        self.cell_buffer: list[str] | None = None
        self.cell_tag: str | None = None
        self.rows_seen = 0
        self.candidates: list[dict[str, object]] = []
        self.debug_rows: list[dict[str, object]] = []
        self.all_rows: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_map = dict(attrs)
        if tag in {"h2", "h3", "h4", "h5"}:
            self.heading_buffer = []
        elif tag == "table":
            classes = set(str(attrs_map.get("class") or "").split())
            skip = self.table_skip_depth > 0 or bool(classes & {"navbox", "navbox-inner", "wraplinks"})
            self.table_skip_stack.append(skip)
            self.table_depth += 1
            if skip:
                self.table_skip_depth += 1
            elif self.table_skip_depth == 0:
                self.engine_code_columns = set()
                self.table_has_id_code_header = False
        elif tag == "tr" and self.table_depth and self.table_skip_depth == 0:
            self.row = []
        elif tag in {"th", "td"} and self.row is not None and self.table_skip_depth == 0:
            self.cell_tag = tag
            self.cell_buffer = []
        elif tag == "dt":
            self.dt_buffer = []
        elif tag == "dd":
            self.dd_buffer = []

    def handle_data(self, data: str) -> None:
        if self.heading_buffer is not None:
            self.heading_buffer.append(data)
        if self.cell_buffer is not None:
            self.cell_buffer.append(data)
        if self.dt_buffer is not None:
            self.dt_buffer.append(data)
        if self.dd_buffer is not None:
            self.dd_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"h2", "h3", "h4", "h5"} and self.heading_buffer is not None:
            heading = clean_text(" ".join(self.heading_buffer))
            if heading:
                self.heading = heading
            self.heading_buffer = None
        elif tag in {"th", "td"} and self.row is not None and self.cell_buffer is not None:
            self.row.append({"tag": self.cell_tag or "td", "text": clean_text(" ".join(self.cell_buffer))})
            self.cell_buffer = None
            self.cell_tag = None
        elif tag == "tr" and self.row is not None:
            self.rows_seen += 1
            self._process_row(self.row, self.rows_seen)
            self.row = None
        elif tag == "dt" and self.dt_buffer is not None:
            self.current_dt_label = clean_text(" ".join(self.dt_buffer))
            self.dt_buffer = None
        elif tag == "dd" and self.dd_buffer is not None:
            self.rows_seen += 1
            self._process_definition_list_row(clean_text(" ".join(self.dd_buffer)), self.rows_seen)
            self.dd_buffer = None
        elif tag == "table" and self.table_depth:
            skipped = self.table_skip_stack.pop() if self.table_skip_stack else False
            if skipped:
                self.table_skip_depth = max(0, self.table_skip_depth - 1)
            self.table_depth -= 1
            if self.table_depth == 0:
                self.engine_code_columns = set()
                self.table_has_id_code_header = False

    def _process_definition_list_row(self, text: str, row_number: int) -> None:
        match = ID_CODE_VALUE_RE.search(text)
        if not match:
            return
        value_text = clean_text(match.group(1))
        codes = extract_codes(value_text)
        if not codes:
            return
        row_text = " | ".join(part for part in (self.current_dt_label, text) if part)
        self.candidates.append({
            "source_row_kind": "definition_list",
            "section_heading": self.heading,
            "source_row_number": row_number,
            "source_row_text": row_text,
            "candidate_value_text": value_text,
            "candidate_codes": codes,
        })
        if len(self.debug_rows) < 120:
            self.debug_rows.append({
                "heading": self.heading,
                "row_number": row_number,
                "definition_term": self.current_dt_label,
                "definition_text": text,
                "candidate_codes": codes,
            })

    def _process_row(self, cells: list[dict[str, str]], row_number: int) -> None:
        if not cells or self.table_skip_depth:
            return
        texts = [cell["text"] for cell in cells]
        if len(self.all_rows) < 120:
            self.all_rows.append({"heading": self.heading, "row_number": row_number, "cells": texts})
        if len(self.debug_rows) < 120 and any("engine" in text.lower() or "code" in text.lower() for text in texts):
            self.debug_rows.append({"heading": self.heading, "row_number": row_number, "cells": texts})
        labels = [index for index, text in enumerate(texts) if is_engine_code_label(text)]
        if labels:
            self.table_has_id_code_header = True
            value_indexes = [index for index in range(len(texts)) if index not in labels]
            values = [texts[index] for index in value_indexes]
            value_cells = [cells[index] for index in value_indexes]
            # A header row can contain decade labels in TD cells; those are not engine codes.
            has_data_cell = any(cell["tag"] == "td" for cell in value_cells)
            if has_data_cell and values and any(extract_codes(value) for value in values):
                self._emit(cells, values, row_number)
            else:
                self.engine_code_columns = {
                    index for index in labels if is_explicit_engine_code_column(texts[index])
                }
            return
        if self.table_has_id_code_header:
            code_values = []
            for text in texts:
                match = DISPLACEMENT_CODE_RE.match(text)
                if match and extract_codes(match.group(1)):
                    code_values.append(match.group(1))
            if code_values:
                self._emit(cells, code_values, row_number)
                return
        if self.engine_code_columns:
            values = [texts[index] for index in sorted(self.engine_code_columns) if index < len(texts)]
            if values and any(extract_codes(value) for value in values):
                self._emit(cells, values, row_number)

    def _emit(self, cells: list[dict[str, str]], values: list[str], row_number: int) -> None:
        row_text = " | ".join(cell["text"] for cell in cells if cell["text"])
        value_text = " | ".join(value for value in values if value)
        if not row_text or not value_text:
            return
        codes = extract_codes(value_text)
        if not codes:
            return
        self.candidates.append({
            "source_row_kind": "table_row",
            "section_heading": self.heading,
            "source_row_number": row_number,
            "source_row_text": row_text,
            "candidate_value_text": value_text,
            "candidate_codes": codes,
        })


def parse_engine_code_candidates_detailed(rendered_html: str) -> tuple[list[dict[str, object]], int, list[dict[str, object]], list[dict[str, object]]]:
    parser = EngineCodeHTMLParser()
    parser.feed(rendered_html)
    parser.close()
    return parser.candidates, parser.rows_seen, parser.debug_rows, parser.all_rows


def parse_engine_code_candidates(rendered_html: str) -> tuple[list[dict[str, object]], int]:
    candidates, rows_seen, _, _ = parse_engine_code_candidates_detailed(rendered_html)
    return candidates, rows_seen


def fetch_json(url: str, attempts: int = 4) -> dict[str, object]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urlopen(request, timeout=45) as response:
                if response.status != 200:
                    raise RuntimeError(f"Wikimedia returned HTTP {response.status}")
                payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise RuntimeError("Wikimedia API returned a non-object response")
                return payload
        except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Wikimedia API request failed after {attempts} attempts: {last_error}")


def fetch_pinned_page(title: str, revision_id: int) -> dict[str, object]:
    query_url = API + "?" + urlencode({
        "action": "query",
        "prop": "revisions",
        "revids": str(revision_id),
        "rvslots": "main",
        "rvprop": "ids|timestamp|content",
        "format": "json",
        "formatversion": "2",
    })
    query = fetch_json(query_url)
    pages = query.get("query", {}).get("pages", [])
    if not isinstance(pages, list) or len(pages) != 1:
        raise RuntimeError(f"Expected exactly one page for revision {revision_id}")
    page = pages[0]
    revisions = page.get("revisions", [])
    if not isinstance(revisions, list) or len(revisions) != 1:
        raise RuntimeError(f"Expected exactly one revision for {revision_id}")
    revision = revisions[0]
    if int(revision.get("revid", -1)) != revision_id:
        raise RuntimeError(f"Revision mismatch for {title}: expected {revision_id}, got {revision.get('revid')}")
    actual_title = str(page.get("title", ""))
    if actual_title != title:
        raise RuntimeError(f"Page title mismatch for revision {revision_id}: {actual_title!r}")
    slots = revision.get("slots", {})
    main = slots.get("main", {}) if isinstance(slots, dict) else {}
    wikitext = main.get("content") or main.get("*")
    if not isinstance(wikitext, str) or not wikitext:
        raise RuntimeError(f"No raw wikitext returned for revision {revision_id}")
    html_url = API + "?" + urlencode({
        "action": "parse",
        "oldid": str(revision_id),
        "prop": "text",
        "format": "json",
        "formatversion": "2",
    })
    rendered = fetch_json(html_url)
    parsed = rendered.get("parse", {})
    rendered_html = parsed.get("text") if isinstance(parsed, dict) else None
    if not isinstance(rendered_html, str) or not rendered_html:
        raise RuntimeError(f"No rendered HTML returned for revision {revision_id}")
    return {
        "title": title,
        "revision_id": revision_id,
        "revision_timestamp": str(revision.get("timestamp", "")),
        "source_url": f"https://en.wikipedia.org/w/index.php?oldid={revision_id}",
        "wikitext": wikitext,
        "wikitext_bytes": wikitext.encode("utf-8"),
        "rendered_html": rendered_html,
        "rendered_html_bytes": rendered_html.encode("utf-8"),
    }


def validate_source_register(path: Path) -> dict[str, object]:
    register = json.loads(path.read_text(encoding="utf-8"))
    sources = register.get("sources", [])
    source = next((item for item in sources if item.get("source_id") == SOURCE_ID), None)
    if not source:
        raise RuntimeError(f"Source register entry {SOURCE_ID} is missing")
    rights = source.get("rights", {})
    required_true = (
        "commercial_use_allowed", "display_allowed", "offline_cache_allowed",
        "bulk_reuse_allowed", "redistribution_allowed", "attribution_required",
        "share_alike_required", "separate_pack_required",
    )
    if rights.get("data_license_status") != LICENSE_ID or rights.get("license_url") != LICENSE_URL:
        raise RuntimeError("Wikipedia CC BY-SA license declaration does not match the expected license")
    if any(rights.get(field) is not True for field in required_true):
        raise RuntimeError("Wikipedia reuse/attribution/share-alike rights are not explicitly enabled")
    if source.get("product_import_allowed") is not False or source.get("market_scope") != ["UNKNOWN"]:
        raise RuntimeError("Wikipedia source register must remain candidate-only and market UNKNOWN")
    expected = {page["title"]: int(page["revision_id"]) for page in source.get("pages", [])}
    if expected != PAGES:
        raise RuntimeError("Pinned Wikipedia revision set differs from the reviewed source register")
    quality = source.get("quality_review", {})
    if quality.get("status") != "not_approved_for_technical_use":
        raise RuntimeError("Wikipedia source quality gate must remain not approved for technical use")
    return source


def build_database(output: Path, pages: list[dict[str, object]], source_manifest_sha: str, snapshot_sha: str, built_at: str) -> dict[str, int]:
    db_path = output / "wikipedia-vag-engine-candidates.sqlite"
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA user_version=2")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.executescript("""
            CREATE TABLE source_registry (
                source_id TEXT PRIMARY KEY,
                publisher TEXT NOT NULL,
                data_license TEXT NOT NULL,
                license_url TEXT NOT NULL,
                rights_status TEXT NOT NULL,
                commercial_use_allowed INTEGER NOT NULL CHECK (commercial_use_allowed=1),
                display_allowed INTEGER NOT NULL CHECK (display_allowed=1),
                offline_cache_allowed INTEGER NOT NULL CHECK (offline_cache_allowed=1),
                bulk_reuse_allowed INTEGER NOT NULL CHECK (bulk_reuse_allowed=1),
                redistribution_allowed INTEGER NOT NULL CHECK (redistribution_allowed=1),
                attribution_required INTEGER NOT NULL CHECK (attribution_required=1),
                share_alike_required INTEGER NOT NULL CHECK (share_alike_required=1),
                separate_pack_required INTEGER NOT NULL CHECK (separate_pack_required=1),
                market_scope TEXT NOT NULL CHECK (market_scope='UNKNOWN'),
                applicability_precision TEXT NOT NULL CHECK (applicability_precision='community_engine_code_candidate_only'),
                review_status TEXT NOT NULL CHECK (review_status='candidate'),
                source_snapshot_sha256 TEXT NOT NULL CHECK (length(source_snapshot_sha256)=64),
                source_manifest_sha256 TEXT NOT NULL CHECK (length(source_manifest_sha256)=64),
                built_at_utc TEXT NOT NULL
            );
            CREATE TABLE source_documents (
                revision_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                source_url TEXT NOT NULL,
                revision_timestamp TEXT NOT NULL,
                wikitext_sha256 TEXT NOT NULL CHECK (length(wikitext_sha256)=64),
                rendered_html_sha256 TEXT NOT NULL CHECK (length(rendered_html_sha256)=64),
                wikitext_bytes INTEGER NOT NULL CHECK (wikitext_bytes>0),
                rendered_html_bytes INTEGER NOT NULL CHECK (rendered_html_bytes>0),
                quality_warnings_json TEXT NOT NULL,
                source_snapshot_sha256 TEXT NOT NULL CHECK (length(source_snapshot_sha256)=64)
            );
            CREATE TABLE engine_code_candidates (
                candidate_id INTEGER PRIMARY KEY,
                candidate_code TEXT NOT NULL,
                source_revision_id INTEGER NOT NULL REFERENCES source_documents(revision_id),
                source_title TEXT NOT NULL,
                source_url TEXT NOT NULL,
                section_heading TEXT,
                source_row_kind TEXT NOT NULL CHECK (source_row_kind IN ('definition_list','table_row')),
                source_row_number INTEGER NOT NULL CHECK (source_row_number>0),
                source_row_text TEXT NOT NULL,
                candidate_value_text TEXT NOT NULL,
                source_row_sha256 TEXT NOT NULL CHECK (length(source_row_sha256)=64),
                source_snapshot_sha256 TEXT NOT NULL CHECK (length(source_snapshot_sha256)=64),
                source_manifest_sha256 TEXT NOT NULL CHECK (length(source_manifest_sha256)=64),
                market_scope TEXT NOT NULL CHECK (market_scope='UNKNOWN'),
                applicability_precision TEXT NOT NULL CHECK (applicability_precision='community_engine_code_candidate_only'),
                review_status TEXT NOT NULL CHECK (review_status='candidate'),
                product_import_allowed INTEGER NOT NULL CHECK (product_import_allowed=0),
                exact_vehicle_fitment INTEGER NOT NULL CHECK (exact_vehicle_fitment=0),
                generation_year_fitment INTEGER NOT NULL CHECK (generation_year_fitment=0),
                engine_gearbox_fitment INTEGER NOT NULL CHECK (engine_gearbox_fitment=0),
                ecu_fitment INTEGER NOT NULL CHECK (ecu_fitment=0),
                dtc_fitment INTEGER NOT NULL CHECK (dtc_fitment=0),
                repair_use_allowed INTEGER NOT NULL CHECK (repair_use_allowed=0),
                diagnostic_execution_allowed INTEGER NOT NULL CHECK (diagnostic_execution_allowed=0),
                UNIQUE(source_revision_id, source_row_sha256, candidate_code)
            );
            CREATE INDEX idx_wikipedia_engine_candidate_code ON engine_code_candidates(candidate_code);
            CREATE INDEX idx_wikipedia_engine_candidate_title ON engine_code_candidates(source_title);
        """)
        connection.execute(
            "INSERT INTO source_registry VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                SOURCE_ID, "Wikipedia contributors", LICENSE_ID, LICENSE_URL, "approved_by_published_license",
                1, 1, 1, 1, 1, 1, 1, 1, "UNKNOWN", "community_engine_code_candidate_only",
                "candidate", snapshot_sha, source_manifest_sha, built_at,
            ),
        )
        candidate_id = 0
        row_count = 0
        unique_codes: set[str] = set()
        for page in pages:
            connection.execute(
                "INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    page["revision_id"], page["title"], page["source_url"], page["revision_timestamp"],
                    page["wikitext_sha256"], page["rendered_html_sha256"], page["wikitext_bytes"],
                    page["rendered_html_bytes"], json.dumps(page["quality_warnings"], ensure_ascii=False),
                    snapshot_sha,
                ),
            )
            for row in page["candidate_rows"]:
                row_hash = sha256_bytes(
                    canonical_json({
                        "title": page["title"],
                        "revision_id": page["revision_id"],
                        "source_row_kind": row.get("source_row_kind", "table_row"),
                        "section_heading": row["section_heading"],
                        "source_row_number": row["source_row_number"],
                        "source_row_text": row["source_row_text"],
                    })
                )
                for code in row["candidate_codes"]:
                    candidate_id += 1
                    row_count += 1
                    unique_codes.add(str(code))
                    connection.execute(
                        """INSERT INTO engine_code_candidates (
                            candidate_id,candidate_code,source_revision_id,source_title,source_url,
                            section_heading,source_row_kind,source_row_number,source_row_text,candidate_value_text,
                            source_row_sha256,source_snapshot_sha256,source_manifest_sha256,
                            market_scope,applicability_precision,review_status,product_import_allowed,
                            exact_vehicle_fitment,generation_year_fitment,engine_gearbox_fitment,
                            ecu_fitment,dtc_fitment,repair_use_allowed,diagnostic_execution_allowed
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            candidate_id, code, page["revision_id"], page["title"], page["source_url"],
                            row["section_heading"], row.get("source_row_kind", "table_row"),
                            row["source_row_number"], row["source_row_text"], row["candidate_value_text"],
                            row_hash, snapshot_sha, source_manifest_sha,
                            "UNKNOWN", "community_engine_code_candidate_only", "candidate", 0,
                            0, 0, 0, 0, 0, 0, 0,
                        ),
                    )
        connection.commit()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign_keys:
            raise RuntimeError(f"Research SQLite integrity failed: integrity={integrity}, foreign_keys={len(foreign_keys)}")
        invalid = connection.execute(
            """SELECT count(*) FROM engine_code_candidates
               WHERE market_scope!='UNKNOWN' OR applicability_precision!='community_engine_code_candidate_only'
                  OR review_status!='candidate' OR product_import_allowed!=0 OR exact_vehicle_fitment!=0
                  OR generation_year_fitment!=0 OR engine_gearbox_fitment!=0 OR ecu_fitment!=0
                  OR dtc_fitment!=0 OR repair_use_allowed!=0 OR diagnostic_execution_allowed!=0
                  OR length(source_row_sha256)!=64 OR length(source_snapshot_sha256)!=64
                  OR length(source_manifest_sha256)!=64"""
        ).fetchone()[0]
        if invalid:
            raise RuntimeError(f"Candidate-only database gate failed for {invalid} rows")
        return {
            "source_documents": len(pages),
            "candidate_rows": row_count,
            "unique_candidate_codes": len(unique_codes),
            "source_rows_with_codes": sum(len(page["candidate_rows"]) for page in pages),
        }
    finally:
        connection.close()


def build_pack(source: dict[str, object], output: Path) -> dict[str, object]:
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"Refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    snapshot_dir = output / "source-snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    page_specs = {page["title"]: page for page in source["pages"]}
    pages: list[dict[str, object]] = []
    for title, revision_id in PAGES.items():
        spec = page_specs[title]
        fetched = fetch_pinned_page(title, revision_id)
        wikitext_bytes = fetched.pop("wikitext_bytes")
        rendered_html_bytes = fetched.pop("rendered_html_bytes")
        wikitext = str(fetched.pop("wikitext"))
        rendered_html = str(fetched.pop("rendered_html"))
        wikitext_sha = sha256_bytes(wikitext_bytes)
        rendered_sha = sha256_bytes(rendered_html_bytes)
        (snapshot_dir / f"{revision_id}.wikitext").write_bytes(wikitext_bytes)
        (snapshot_dir / f"{revision_id}.html").write_bytes(rendered_html_bytes)
        candidates, rows_seen, debug_rows, all_rows = parse_engine_code_candidates_detailed(rendered_html)
        print(json.dumps({
            "page": title,
            "revision_id": revision_id,
            "rows_seen": rows_seen,
            "candidate_rows": len(candidates),
            "candidate_codes": sorted({code for row in candidates for code in row["candidate_codes"]}),
            "engine_or_code_rows": debug_rows[:40],
            "table_row_sample": all_rows[:80],
        }, ensure_ascii=False), file=sys.stderr)
        pages.append({
            "title": title,
            "revision_id": revision_id,
            "revision_timestamp": fetched["revision_timestamp"],
            "source_url": fetched["source_url"],
            "wikitext_sha256": wikitext_sha,
            "rendered_html_sha256": rendered_sha,
            "wikitext_bytes": len(wikitext_bytes),
            "rendered_html_bytes": len(rendered_html_bytes),
            "quality_warnings": spec.get("quality_warnings", []),
            "candidate_rows": candidates,
            "rows_seen": rows_seen,
        })
        time.sleep(0.5)

    snapshot_payload = [
        {
            "title": page["title"],
            "revision_id": page["revision_id"],
            "wikitext_sha256": page["wikitext_sha256"],
            "rendered_html_sha256": page["rendered_html_sha256"],
        }
        for page in pages
    ]
    snapshot_sha = sha256_bytes(canonical_json(snapshot_payload))
    total_candidates = sum(sum(len(row["candidate_codes"]) for row in page["candidate_rows"]) for page in pages)
    unique_codes = sorted({code for page in pages for row in page["candidate_rows"] for code in row["candidate_codes"]})
    if total_candidates < 30 or len(unique_codes) < 30:
        raise RuntimeError(f"Unexpectedly small Wikipedia candidate extraction: rows={total_candidates}, unique_codes={len(unique_codes)}")

    source_manifest = {
        "schema_version": 2,
        "source_id": SOURCE_ID,
        "publisher": "Wikipedia contributors",
        "source_repository": "https://en.wikipedia.org/",
        "data_license": LICENSE_ID,
        "license_url": LICENSE_URL,
        "rights_status": "approved_by_published_license",
        "commercial_use_allowed": True,
        "display_allowed": True,
        "offline_cache_allowed": True,
        "bulk_reuse_allowed": True,
        "redistribution_allowed": True,
        "attribution_required": True,
        "share_alike_required": True,
        "separate_pack_required": True,
        "market_scope": "UNKNOWN",
        "applicability_precision": "community_engine_code_candidate_only",
        "review_status": "candidate",
        "quality_review_status": "not_approved_for_technical_use",
        "quality_warnings": source["quality_review"]["blocking_warnings"],
        "extraction_policy": {
            "definition_list_rule": "Extract only dd values containing an explicit ID code: or engine ID code: label.",
            "table_rule": "Extract only table cells under explicit engine ID/code headers.",
            "excluded_table_classes": ["navbox", "navbox-inner", "wraplinks"],
            "candidate_normalization": "Uppercase alphanumeric tokens of 2-5 characters; known engine-family, transmission, market and emissions annotation tokens are excluded.",
            "candidate_only": True,
        },
        "source_snapshot_sha256": snapshot_sha,
        "pages": [
            {
                "title": page["title"],
                "revision_id": page["revision_id"],
                "revision_timestamp": page["revision_timestamp"],
                "source_url": page["source_url"],
                "wikitext_sha256": page["wikitext_sha256"],
                "rendered_html_sha256": page["rendered_html_sha256"],
                "wikitext_bytes": page["wikitext_bytes"],
                "rendered_html_bytes": page["rendered_html_bytes"],
                "quality_warnings": page["quality_warnings"],
                "rows_seen": page["rows_seen"],
                "extracted_candidate_rows": len(page["candidate_rows"]),
            }
            for page in pages
        ],
        "counts": {
            "source_documents": len(pages),
            "candidate_rows": total_candidates,
            "unique_candidate_codes": len(unique_codes),
            "source_rows_with_codes": sum(len(page["candidate_rows"]) for page in pages),
        },
        "candidate_only": {
            "product_import_allowed": False,
            "exact_vehicle_fitment": False,
            "generation_year_fitment": False,
            "engine_gearbox_fitment": False,
            "ecu_fitment": False,
            "dtc_fitment": False,
            "repair_use_allowed": False,
            "diagnostic_execution_allowed": False,
        },
        "attribution": "Adapted from Wikipedia contributors, four pinned Volkswagen Group engine-list articles; each page title, revision ID and URL are listed in ATTRIBUTION.md. Licensed under CC BY-SA 4.0. Changes by VAG TECH PRO: HTML row extraction, candidate-code normalization and SQLite packaging.",
    }
    source_manifest_path = output / "source-manifest.json"
    source_manifest_path.write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_manifest_sha = sha256_file(source_manifest_path)
    built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    counts = build_database(output, pages, source_manifest_sha, snapshot_sha, built_at)
    database_path = output / "wikipedia-vag-engine-candidates.sqlite"
    database_sha = sha256_file(database_path)

    attribution_lines = [
        "# Attribution — Wikipedia VAG engine-code candidates",
        "",
        "This is a separately licensed CC BY-SA 4.0 research pack. It is not OEM data.",
        "",
        "Adapted from Wikipedia contributors:",
    ]
    for page in pages:
        attribution_lines.append(f"- [{page['title']}]({page['source_url']}), revision {page['revision_id']}.")
    attribution_lines += [
        "",
        f"License: [Creative Commons Attribution-ShareAlike 4.0 International]({LICENSE_URL}).",
        "Changes made by VAG TECH PRO: extraction of explicit ID-code values from article definition lists and explicit engine-ID table columns; navigation-box tables are excluded; token normalization, source-row hashing and SQLite packaging.",
        "Market scope is UNKNOWN. All values are unverified community candidates. No model, generation, year, engine/gearbox pair, ECU, DTC, repair procedure or diagnostic applicability is established.",
        "The candidate database is kept separate and must remain under CC BY-SA 4.0 with attribution and ShareAlike notices.",
    ]
    attribution_path = output / "ATTRIBUTION.md"
    attribution_path.write_text("\n".join(attribution_lines) + "\n", encoding="utf-8")
    license_path = output / "LICENSE-NOTICE.txt"
    license_path.write_text(
        "Data and extracted article text: CC BY-SA 4.0.\n"
        f"License URL: {LICENSE_URL}\n"
        "Attribution and ShareAlike are required. This notice is not a substitute for the full license.\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 2,
        "pack_id": PACK_ID,
        "publisher": "Wikipedia contributors",
        "source_id": SOURCE_ID,
        "source_repository": "https://en.wikipedia.org/",
        "source_revision": "four_pinned_article_revisions",
        "data_license": LICENSE_ID,
        "license_url": LICENSE_URL,
        "rights_status": "approved_by_published_license",
        "commercial_use_allowed": True,
        "display_allowed": True,
        "offline_cache_allowed": True,
        "bulk_reuse_allowed": True,
        "redistribution_allowed": True,
        "attribution_required": True,
        "share_alike_required": True,
        "separate_pack_required": True,
        "market_scope": "UNKNOWN",
        "applicability_precision": "community_engine_code_candidate_only",
        "verification_status": "community_reference_unverified",
        "quality_review_status": "not_approved_for_technical_use",
        "candidate_only": True,
        "product_import_allowed": False,
        "exact_vehicle_fitment": False,
        "generation_year_fitment": False,
        "engine_gearbox_fitment": False,
        "ecu_fitment": False,
        "dtc_fitment": False,
        "repair_use_allowed": False,
        "diagnostic_execution_allowed": False,
        "source_snapshot_sha256": snapshot_sha,
        "source_manifest_sha256": source_manifest_sha,
        "database_file": database_path.name,
        "database_sha256": database_sha,
        "attribution_file": "ATTRIBUTION.md",
        "attribution_sha256": sha256_file(attribution_path),
        "license_notice_file": "LICENSE-NOTICE.txt",
        "license_notice_sha256": sha256_file(license_path),
        "built_at_utc": built_at,
        "counts": counts,
        "pages": source_manifest["pages"],
        "quality_warnings": source_manifest["quality_warnings"],
        "extraction_policy": {
            "definition_list_rule": "Extract only dd values containing an explicit ID code: or engine ID code: label.",
            "table_rule": "Extract only table cells under explicit engine ID/code headers.",
            "excluded_table_classes": ["navbox", "navbox-inner", "wraplinks"],
            "candidate_normalization": "Uppercase alphanumeric tokens of 2-5 characters; known engine-family, transmission, market and emissions annotation tokens are excluded.",
            "candidate_only": True,
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "pack_id": PACK_ID,
        "manifest_sha256": sha256_file(manifest_path),
        "source_manifest_sha256": source_manifest_sha,
        "source_snapshot_sha256": snapshot_sha,
        "database_sha256": database_sha,
        "counts": counts,
        "market_scope": "UNKNOWN",
        "applicability_precision": "community_engine_code_candidate_only",
        "product_import_allowed": False,
        "diagnostic_execution_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-register", type=Path, default=Path("data/source-manifests/vag-factory-source-register.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        source = validate_source_register(args.source_register)
        result = build_pack(source, args.output_dir.resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
