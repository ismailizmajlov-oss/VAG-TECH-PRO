#!/usr/bin/env python3
"""Probe only the official Rosstandart recall open-data landing/archive pages.

This script deliberately does not download discovered data files. It records page
metadata, same-host candidate links and a SHA-256 of each small HTML response so
a later rights/schema review can decide whether a separate data acquisition is safe.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

PAGES = (
    "https://easy.gost.ru/opendata/7706406291-recallcampaigns/",
    "https://easy.gost.ru/opendata/7706406291-recallcampaigns/archive/",
)
OFFICIAL_HOST = "easy.gost.ru"
MAX_HTML_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 30
USER_AGENT = "VAG-TECH-PRO-open-data-rights-probe/1.0 (metadata-only; no file downloads)"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self._anchor: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "a" and values.get("href"):
            self._anchor = {
                "href": values["href"].strip(),
                "text": "",
                "rel": values.get("rel", "").strip(),
                "type": values.get("type", "").strip(),
            }
        if tag.lower() in {"link", "meta"}:
            href = values.get("href") or values.get("content") or ""
            rel = values.get("rel", "").lower()
            name = (values.get("name") or values.get("property") or "").lower()
            if href and ("license" in rel or "license" in name or "terms" in name):
                self.links.append({"href": href.strip(), "text": "", "rel": rel, "type": values.get("type", "")})

    def handle_data(self, data: str) -> None:
        if self._anchor is not None:
            self._anchor["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._anchor is not None:
            self.links.append(self._anchor)
            self._anchor = None


def _candidate_link(base_url: str, link: dict[str, str]) -> dict[str, str] | None:
    absolute = urljoin(base_url, link["href"])
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    text = link.get("text", "").strip()
    href = absolute.lower()
    signal = (
        re.search(r"\.(csv|zip|7z|rar|xml|json|xlsx?|ods)(?:$|[?#])", href) is not None
        or any(token in text.lower() for token in ("скачать", "download", "архив", "выгруз", "csv", "xml", "json"))
        or "opendata" in href and "archive" in href
    )
    if not signal:
        return None
    return {
        "url": absolute,
        "host": parsed.hostname,
        "same_official_host": parsed.hostname == OFFICIAL_HOST,
        "text": text[:300],
        "rel": link.get("rel", ""),
        "type": link.get("type", ""),
    }


def fetch_page(url: str) -> dict[str, object]:
    result: dict[str, object] = {
        "requested_url": url,
        "retrieved": False,
        "status": None,
        "final_url": None,
        "content_type": None,
        "content_length_header": None,
        "last_modified": None,
        "etag": None,
        "html_sha256": None,
        "truncated": False,
        "candidate_file_links": [],
        "terms_links": [],
        "error": None,
    }
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            result["status"] = getattr(response, "status", None)
            result["final_url"] = response.geturl()
            result["content_type"] = response.headers.get("Content-Type")
            result["content_length_header"] = response.headers.get("Content-Length")
            result["last_modified"] = response.headers.get("Last-Modified")
            result["etag"] = response.headers.get("ETag")
            final_host = urlparse(response.geturl()).hostname
            if final_host != OFFICIAL_HOST:
                result["error"] = "redirected_outside_official_host"
                return result
            if "html" not in str(result["content_type"] or "").lower():
                result["error"] = "official_page_did_not_return_html"
                return result
            raw = response.read(MAX_HTML_BYTES + 1)
            if len(raw) > MAX_HTML_BYTES:
                raw = raw[:MAX_HTML_BYTES]
                result["truncated"] = True
            result["html_sha256"] = hashlib.sha256(raw).hexdigest()
            parser = LinkParser()
            parser.feed(raw.decode("utf-8", errors="replace"))
            candidates = []
            terms = []
            for link in parser.links:
                absolute = urljoin(response.geturl(), link["href"])
                host = urlparse(absolute).hostname
                if host == OFFICIAL_HOST:
                    candidate = _candidate_link(response.geturl(), link)
                    if candidate:
                        candidates.append(candidate)
                elif host in {"data.gov.ru", "www.data.gov.ru", "pravo.ppt.ru"} and (
                    "услов" in link.get("text", "").lower()
                    or "license" in link.get("rel", "").lower()
                    or "terms" in link.get("text", "").lower()
                ):
                    terms.append({"url": absolute, "text": link.get("text", "")[:300]})
            result["candidate_file_links"] = sorted({x["url"]: x for x in candidates}.values(), key=lambda x: x["url"])
            result["terms_links"] = sorted({x["url"]: x for x in terms}.values(), key=lambda x: x["url"])
            result["retrieved"] = True
    except Exception as exc:  # network errors are recorded, not hidden
        result["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="rosstandart-recall-open-data-probe.json")
    args = parser.parse_args()
    report = {
        "schema_version": 1,
        "source_id": "rosstandart-recall-campaigns-open-data",
        "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "official_host": OFFICIAL_HOST,
        "pages": [fetch_page(url) for url in PAGES],
        "data_file_downloaded": False,
        "source_snapshot_sha256": None,
        "vin_level_rows_downloaded": False,
        "decision": "metadata_probe_only; no data file is downloaded by this script",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    retrieved = sum(1 for page in report["pages"] if page["retrieved"])
    candidates = sum(len(page["candidate_file_links"]) for page in report["pages"])
    print(f"Rosstandart metadata probe: pages_retrieved={retrieved}/{len(PAGES)} candidate_file_links={candidates}")
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
