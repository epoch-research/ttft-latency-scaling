#!/usr/bin/env python3
"""Create the public JSONL and chronological schedules from private raw logs.

This utility is for release maintenance. The analysis consumes the already
sanitized files checked into ``data/raw`` and never needs access to the private
source directory.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SESSIONS = {
    "20260813T155415Z-6998d614": ("final", "gpt-5.6-terra"),
    "20260814T140715Z-bee825d8": ("final", "gpt-5.6-sol"),
    "20260814T154718Z-5dc271b9": ("final", "claude-sonnet-5"),
    "20260813T163222Z-b3406d60": ("final", "claude-opus-5"),
    "20260812T191605Z-bae8e752": ("supporting", "claude-sonnet-5"),
    "20260812T192643Z-50c12a81": ("supporting", "claude-sonnet-5"),
}

REDACTED_FIELDS = {
    "hostname",
    "request_id",
    "response_id",
    "retry_after",
    "ratelimit_reset_tokens",
    "ratelimit_remaining_tokens",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Directory containing private JSONL logs")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Reproducibility-repository root",
    )
    args = parser.parse_args()

    schedule_dir = args.root / "data" / "schedules"
    schedule_dir.mkdir(parents=True, exist_ok=True)

    for session_id, (role, _model) in SESSIONS.items():
        source = args.source / f"{session_id}.jsonl"
        destination = args.root / "data" / "raw" / role / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        records = [json.loads(line) for line in source.read_text().splitlines() if line]

        with destination.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                for field in REDACTED_FIELDS:
                    record.pop(field, None)
                handle.write(json.dumps(record, separators=(",", ":")) + "\n")

        measured = [
            record
            for record in records
            if record.get("type") == "sample" and record.get("kind") == "measured"
        ]
        with (schedule_dir / f"{session_id}.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "sequence",
                    "block",
                    "target_tokens",
                    "request_started_at",
                    "request_completed_at",
                ],
            )
            writer.writeheader()
            for sequence, record in enumerate(measured, start=1):
                writer.writerow(
                    {
                        "sequence": sequence,
                        "block": record["repetition"] + 1,
                        "target_tokens": record["target_tokens"],
                        "request_started_at": record.get("request_started_at", ""),
                        "request_completed_at": record.get("request_completed_at", ""),
                    }
                )


if __name__ == "__main__":
    main()
