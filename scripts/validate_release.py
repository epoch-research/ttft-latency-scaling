#!/usr/bin/env python3
"""Validate the public evidence bundle without third-party dependencies."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REDACTED = {
    "hostname",
    "request_id",
    "response_id",
    "retry_after",
    "ratelimit_reset_tokens",
    "ratelimit_remaining_tokens",
}


def fail(message: str) -> None:
    raise AssertionError(message)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def main() -> None:
    with (ROOT / "data/session_manifest.csv").open(newline="") as handle:
        manifest = list(csv.DictReader(handle))

    for specification in manifest:
        path = ROOT / specification["file"]
        records = read_jsonl(path)
        header = records[0]
        if header.get("type") != "session":
            fail(f"{path}: first record is not a session header")
        if header.get("session") != specification["session_id"]:
            fail(f"{path}: session ID mismatch")
        present_redactions = set().union(
            *(REDACTED.intersection(record) for record in records)
        )
        if present_redactions:
            fail(f"{path}: public log contains {sorted(present_redactions)}")

        samples = [
            record
            for record in records
            if record.get("type") == "sample" and record.get("kind") == "measured"
        ]
        expected_requests = int(specification["expected_requests"])
        if len(samples) != expected_requests:
            fail(f"{path}: expected {expected_requests} measurements, got {len(samples)}")
        expected_lengths = {
            int(value) for value in specification["context_lengths"].split(";")
        }
        if {sample["target_tokens"] for sample in samples} != expected_lengths:
            fail(f"{path}: context-length set mismatch")
        expected_blocks = int(specification["expected_blocks"])
        counts = Counter(sample["target_tokens"] for sample in samples)
        if specification["role"] == "astra-api":
            if header["corpus_sha256"] != "075768889cfef63bcbb967fa0204b6048201fdfe896124915f75e8dadc8b9e75":
                fail(f"{path}: Astra corpus hash mismatch")
            if set(counts.values()) != {expected_blocks}:
                fail(f"{path}: Astra measurements are not balanced")
            blocks = {}
            for sample in samples:
                blocks.setdefault(sample["repetition"], []).append(sample["target_tokens"])
                if not sample.get("valid") or sample.get("model") != "gpt-6-astra":
                    fail(f"{path}: invalid or non-Astra measurement")
                if sample.get("provider") != "openai" or sample.get("mode") != "shared_prefix_cached":
                    fail(f"{path}: unexpected collection route")
                expected = {"cache_read_tokens": 2051, "cache_write_tokens": 0,
                            "reasoning_tokens": 0, "output_tokens": 5,
                            "max_output_tokens": 512, "reasoning_effort": "low",
                            "output_preview": "OK", "status_code": 200,
                            "returned_model": "gpt-6-astra",
                            "requested_service_tier": "default",
                            "returned_service_tier": "default"}
                for key, value in expected.items():
                    if sample.get(key) != value:
                        fail(f"{path}: unexpected {key}")
                if sample["total_input_tokens"] != sample["target_tokens"] - 2:
                    fail(f"{path}: input token count mismatch")
                if sample["new_input_tokens"] + sample["cache_read_tokens"] != sample["total_input_tokens"]:
                    fail(f"{path}: token accounting mismatch")
                if not 0 < sample["ttft_ns"] <= sample["total_ns"]:
                    fail(f"{path}: invalid timing interval")
            if len(blocks) != expected_blocks or any(
                len(v) != len(expected_lengths) or set(v) != expected_lengths
                for v in blocks.values()
            ):
                fail(f"{path}: incomplete Astra block")
            setup = [r for r in records if r.get("kind") == "cache_setup"]
            if len(setup) != 1 or setup[0].get("cache_write_tokens") != 2051:
                fail(f"{path}: expected one excluded cache-setup request")
            if specification["session_id"] == "20260909T123307Z-1c49feec":
                if any(r.get("type") == "session_end" for r in records):
                    fail(f"{path}: interrupted session unexpectedly has session_end")
            elif records[-1].get("status") != "complete":
                fail(f"{path}: continuation is not complete")
            for record in records:
                if any(k in record for k in ("network_label", "platform", "hard_cost_limit_usd", "thread", "usage")):
                    fail(f"{path}: private metadata or non-API schema")
        if specification["role"] == "final":
            if set(counts.values()) != {expected_blocks}:
                fail(f"{path}: final session is not balanced by length")
            if records[-1].get("type") != "session_end" or records[-1].get("status") != "complete":
                fail(f"{path}: final session lacks a complete session_end")
            cache_read = 2051 if specification["provider"] == "openai" else 2052
            total_offset = 2 if specification["provider"] == "openai" else 6
            for sample in samples:
                if not sample.get("valid"):
                    fail(f"{path}: invalid final measurement")
                if sample.get("cache_read_tokens") != cache_read:
                    fail(f"{path}: unexpected cache read")
                if sample.get("cache_write_tokens") != 0:
                    fail(f"{path}: measured request wrote cache tokens")
                if sample.get("total_input_tokens") != sample["target_tokens"] - total_offset:
                    fail(f"{path}: provider token offset changed")
                if sample.get("reasoning_tokens") not in (0, None):
                    fail(f"{path}: reasoning tokens were generated")
                if sample.get("thinking_blocks", 0) != 0:
                    fail(f"{path}: thinking block was generated")

        schedule_path = ROOT / "data/schedules" / f"{specification['session_id']}.csv"
        with schedule_path.open(newline="") as handle:
            schedule = list(csv.DictReader(handle))
        if len(schedule) != len(samples):
            fail(f"{schedule_path}: schedule length mismatch")
        if [int(row["target_tokens"]) for row in schedule] != [
            sample["target_tokens"] for sample in samples
        ]:
            fail(f"{schedule_path}: schedule order mismatch")
        if specification["role"] == "astra-api":
            for row, sample in zip(schedule, samples):
                if (int(row["block"]) != sample["repetition"] + 1 or
                    row["request_started_at"] != sample["request_started_at"] or
                    row["request_completed_at"] != sample["request_completed_at"]):
                    fail(f"{schedule_path}: chronology differs from raw log")

    corpus = (ROOT / "data/corpus/combined.txt").read_bytes()
    metadata = json.loads((ROOT / "data/corpus/combined.meta.json").read_text())
    if hashlib.sha256(corpus).hexdigest() != metadata["combined_sha256"]:
        fail("combined corpus SHA-256 mismatch")
    corpus_manifest = json.loads((ROOT / "data/corpus/manifest.json").read_text())
    expected_documents = len(corpus_manifest["documents"])
    corpus_text = corpus.decode("utf-8")
    if corpus_text.count("===== DOCUMENT:") != expected_documents:
        fail("combined corpus document count mismatch")
    if corpus_text.count("START: FULL LICENSE") != expected_documents:
        fail("combined corpus does not retain every full Project Gutenberg license")
    if (
        corpus_text.count("Section 5. General Information About Project Gutenberg")
        != expected_documents
    ):
        fail("combined corpus contains a truncated Project Gutenberg license")
    for index, document in enumerate(corpus_text.split("===== DOCUMENT:")[1:], start=1):
        work_start = document.find("*** START OF THE PROJECT GUTENBERG EBOOK")
        opening = document[:work_start] if work_start >= 0 else ""
        if "this ebook is for the use of anyone" not in opening.lower():
            fail(f"combined corpus document {index} lacks its opening use notice")

    print(f"Validated {len(manifest)} sessions and the pinned corpus.")


if __name__ == "__main__":
    main()
