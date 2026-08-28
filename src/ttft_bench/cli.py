from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import random
import socket
import sys
import time
import tomllib
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "benchmark.toml"
NONCE = " ".join("0" for _ in range(16))
FIXED_OUTPUT_PROMPT = (
    "Do not think or analyze. Respond immediately with exactly one word: OK"
)
RESULT_SCHEMA_VERSION = 2
CACHE_COUNT_TOLERANCE = 64
TRANSIENT_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}
SHARED_REQUEST_MAX_ATTEMPTS = 4


def load_config(path: Path) -> dict[str, Any]:
    config = tomllib.loads(path.resolve().read_text())
    config["root"] = path.resolve().parent.parent
    for name, model in config["models"].items():
        model["name"] = name
    return config


def path_for(config: dict[str, Any], name: str) -> Path:
    return (config["root"] / config["paths"][name]).resolve()


def selected(args: argparse.Namespace, config: dict[str, Any]) -> tuple[list[dict], list[int]]:
    names = args.models.split(",") if args.models else list(config["models"])
    unknown = set(names) - set(config["models"])
    if unknown:
        raise ValueError(f"unknown model(s): {', '.join(sorted(unknown))}")
    lengths = (
        [int(value.replace("_", "")) for value in args.lengths.split(",")]
        if args.lengths
        else config["benchmark"]["lengths"]
    )
    if len(lengths) != len(set(lengths)) or any(length <= 0 for length in lengths):
        raise ValueError("lengths must be unique positive integers")
    return [config["models"][name] for name in names], lengths


def repetition_map(value: str | None) -> dict[int, int] | None:
    if not value:
        return None
    result = {}
    for item in value.split(","):
        length, repetitions = item.split(":", 1)
        count = int(repetitions)
        if count <= 0:
            raise ValueError("repetition counts must be positive")
        result[int(length.replace("_", ""))] = count
    return result


# Corpus ---------------------------------------------------------------------


def prepare_corpus(config: dict[str, Any], force: bool) -> Path:
    manifest = json.loads(path_for(config, "manifest").read_text())
    directory = path_for(config, "corpus_dir")
    directory.mkdir(parents=True, exist_ok=True)
    documents = []
    for item in manifest["documents"]:
        destination = directory / f"{item['id']}.txt"
        if force or not destination.exists():
            request = urllib.request.Request(
                item["url"], headers={"User-Agent": "ttft-bench/0.1"}
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                destination.write_bytes(response.read())
        raw = destination.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != item["sha256"]:
            raise ValueError(f"checksum mismatch for {item['id']}: {actual}")
        text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        documents.append(
            f"\n\n===== DOCUMENT: {item['title']} ({item['id']}) =====\n\n{text.strip()}"
        )
    combined = "".join(documents) + "\n"
    output = directory / "combined.txt"
    output.write_text(combined, encoding="utf-8", newline="\n")
    return output


def read_corpus(config: dict[str, Any]) -> tuple[str, str]:
    path = path_for(config, "corpus_dir") / "combined.txt"
    if not path.exists():
        raise ValueError("corpus is missing; run prepare-corpus")
    text = path.read_text(encoding="utf-8")
    return text, hashlib.sha256(text.encode()).hexdigest()


# Provider calls --------------------------------------------------------------


def provider_client(model: dict[str, Any], timeout: float) -> httpx.Client:
    if model["provider"] == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        headers = {"Authorization": f"Bearer {key}"}
        base_url = "https://api.openai.com"
    else:
        key = os.environ.get("ANTHROPIC_API_KEY")
        headers = {"x-api-key": key or "", "anthropic-version": "2023-06-01"}
        base_url = "https://api.anthropic.com"
    if not key:
        variable = "OPENAI_API_KEY" if model["provider"] == "openai" else "ANTHROPIC_API_KEY"
        raise ValueError(f"{variable} is missing from .env")
    return httpx.Client(
        base_url=base_url,
        headers=headers,
        timeout=httpx.Timeout(timeout, connect=30),
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
    )


def blocks(model: dict[str, Any], stable: str, suffix: str, cached: bool) -> list[dict]:
    block_type = "input_text" if model["provider"] == "openai" else "text"
    content = []
    if stable:
        block: dict[str, Any] = {"type": block_type, "text": stable}
        if (
            cached
            and model["provider"] == "openai"
            and model.get("cache_api") != "legacy"
        ):
            block["prompt_cache_breakpoint"] = {"mode": "explicit"}
        elif cached:
            block["cache_control"] = {"type": "ephemeral", "ttl": "5m"}
        content.append(block)
    content.append({"type": block_type, "text": suffix})
    message = {"role": "user", "content": content}
    if model["provider"] == "openai":
        message["type"] = "message"
    return [message]


def count_tokens(
    client: httpx.Client,
    model: dict[str, Any],
    stable: str,
    suffix: str,
    cached: bool,
) -> int:
    if model["provider"] == "openai":
        payload = {
            "model": model["model"],
            "input": blocks(model, stable, suffix, cached),
            "reasoning": {"effort": "none"},
        }
        response = client.post("/v1/responses/input_tokens", json=payload)
    else:
        payload = {
            "model": model["model"],
            "messages": blocks(model, stable, suffix, cached),
            "thinking": {"type": model.get("thinking_type", "disabled")},
        }
        if model.get("effort"):
            payload["output_config"] = {"effort": model["effort"]}
        response = client.post("/v1/messages/count_tokens", json=payload)
    response.raise_for_status()
    return int(response.json()["input_tokens"])


def prompt_parts(
    corpus: str,
    end: int,
    split: int,
    instruction: str,
    cached: bool,
) -> tuple[str, str]:
    if cached:
        stable = "REFERENCE TEXT:\n" + corpus[:split]
        text = corpus[split:end]
        heading = ""
    else:
        stable = ""
        text = corpus[:end]
        heading = "REFERENCE TEXT:\n"
    suffix = f"{heading}{text}\n\nTASK:\n{instruction}\nBenchmark nonce: "
    return stable, suffix


def shorten_cached_suffix(
    client: httpx.Client,
    model: dict[str, Any],
    benchmark: dict[str, Any],
    corpus: str,
    row: dict[str, Any],
    target_tokens: int,
) -> dict[str, Any]:
    """Keep the prepared cached prefix byte-for-byte and shorten only its suffix."""
    stable, suffix = prompt_parts(
        corpus, row["end"], row["split"], benchmark["prompt"], True
    )
    low, high = 0, len(suffix)
    chosen, chosen_tokens = suffix, count_tokens(client, model, "", suffix + NONCE, False)
    while low <= high:
        start = (low + high) // 2
        candidate = suffix[start:]
        tokens = count_tokens(client, model, "", candidate + NONCE, False)
        if tokens <= target_tokens:
            chosen, chosen_tokens = candidate, tokens
            high = start - 1
        else:
            low = start + 1
    if chosen_tokens > target_tokens:
        raise ValueError(f"could not fit cached suffix within {target_tokens:,} tokens")
    result = dict(row)
    result.update(
        suffix_override=chosen,
        new_estimate=chosen_tokens,
        counted=row["cache_estimate"] + chosen_tokens,
        target=row["cache_estimate"] + chosen_tokens,
        prompt_sha256=hashlib.sha256(
            f"{model['model']}:True:{stable}:{chosen}".encode()
        ).hexdigest(),
    )
    return result


def shared_prefix_rows(
    client: httpx.Client,
    model: dict[str, Any],
    benchmark: dict[str, Any],
    corpus: str,
    rows: list[dict[str, Any]],
    prefix_tokens: int,
) -> list[dict[str, Any]]:
    """Build target-length prompts that all share one small cached prefix."""
    base = min(rows, key=lambda row: row["target"])
    low, high, chosen = 0, base["end"], None
    while low <= high:
        split = (low + high) // 2
        stable, suffix = prompt_parts(
            corpus, base["end"], split, benchmark["prompt"], True
        )
        total = count_tokens(client, model, stable, suffix + NONCE, True)
        new = count_tokens(client, model, "", suffix + NONCE, False)
        cached_count = total - new
        if cached_count >= prefix_tokens:
            chosen, high = split, split - 1
        else:
            low = split + 1
    if chosen is None:
        raise ValueError(f"could not construct a {prefix_tokens:,}-token shared prefix")

    result = []
    expected_prefix = None
    stable_prefix_sha256 = None
    for source in rows:
        low, high, best = chosen, len(corpus), chosen
        while low <= high:
            end = (low + high) // 2
            stable, suffix = prompt_parts(
                corpus, end, chosen, benchmark["prompt"], True
            )
            total = count_tokens(client, model, stable, suffix + NONCE, True)
            if total <= source["target"]:
                best, low = end, end + 1
            else:
                high = end - 1
        stable, suffix = prompt_parts(
            corpus, best, chosen, benchmark["prompt"], True
        )
        total = count_tokens(client, model, stable, suffix + NONCE, True)
        new = count_tokens(client, model, "", suffix + NONCE, False)
        cached_count = total - new
        expected_prefix = cached_count if expected_prefix is None else expected_prefix
        if cached_count != expected_prefix:
            raise RuntimeError("shared cached-prefix count changed across target lengths")
        stable_digest = hashlib.sha256(stable.encode()).hexdigest()
        stable_prefix_sha256 = stable_digest if stable_prefix_sha256 is None else stable_prefix_sha256
        if stable_digest != stable_prefix_sha256:
            raise RuntimeError("shared cached-prefix content changed across target lengths")
        row = dict(source)
        row.update(
            mode="cached",
            report_mode="shared_prefix_cached",
            counted=total,
            end=best,
            split=chosen,
            new_estimate=new,
            cache_estimate=cached_count,
            shared_cache_prefix_requested_tokens=prefix_tokens,
            stable_prefix_sha256=stable_digest,
            prompt_sha256=hashlib.sha256(
                f"{model['model']}:shared:{stable}:{suffix}".encode()
            ).hexdigest(),
        )
        result.append(row)
    return result


# Prompt sizing ---------------------------------------------------------------


def prompt_file(config: dict[str, Any], model: dict[str, Any]) -> Path:
    safe = model["model"].replace("/", "_")
    return path_for(config, "prompt_dir") / f"{model['provider']}__{safe}.json"


def fit_prompt(
    client: httpx.Client,
    model: dict[str, Any],
    benchmark: dict[str, Any],
    corpus: str,
    corpus_hash: str,
    requested: int,
    cached: bool,
) -> dict[str, Any]:
    limit = min(
        model["context_window"] - benchmark["max_output_tokens"] - benchmark["context_safety_tokens"],
        model.get("max_input_tokens", model["context_window"]),
    )
    target = min(requested, limit)

    def split_guess(end: int) -> int:
        if not cached:
            return 0
        fraction = min(1, benchmark["cached_suffix_tokens"] / target)
        return max(0, end - round(end * fraction))

    low, high, best = 0, len(corpus), 0
    while low <= high:
        end = (low + high) // 2
        split = split_guess(end)
        stable, suffix = prompt_parts(corpus, end, split, benchmark["prompt"], cached)
        tokens = count_tokens(client, model, stable, suffix + NONCE, cached)
        if tokens <= target:
            best, low = end, end + 1
        else:
            high = end - 1
    if best == len(corpus):
        raise ValueError(f"corpus is too small for {requested:,} tokens")

    split = split_guess(best)
    new_tokens = target
    if cached:
        # Refine the split until the changing suffix is close to 10k provider tokens.
        low, high, chosen = 0, best, best
        while low <= high:
            candidate = (low + high) // 2
            _, suffix = prompt_parts(corpus, best, candidate, benchmark["prompt"], True)
            tokens = count_tokens(client, model, "", suffix + NONCE, False)
            if tokens <= benchmark["cached_suffix_tokens"]:
                chosen, new_tokens, high = candidate, tokens, candidate - 1
            else:
                low = candidate + 1
        split = chosen

    stable, suffix = prompt_parts(corpus, best, split, benchmark["prompt"], cached)
    total = count_tokens(client, model, stable, suffix + NONCE, cached)
    while total > target and best > split:
        best -= max(1, (total - target) * 3)
        split = min(split, best)
        stable, suffix = prompt_parts(corpus, best, split, benchmark["prompt"], cached)
        total = count_tokens(client, model, stable, suffix + NONCE, cached)
    digest = hashlib.sha256(f"{model['model']}:{cached}:{stable}:{suffix}".encode()).hexdigest()
    return {
        "mode": "cached" if cached else "uncached",
        "target": requested,
        "counted": total,
        "end": best,
        "split": split,
        "new_estimate": new_tokens if cached else total,
        "cache_estimate": max(0, total - new_tokens) if cached else 0,
        "prompt_sha256": digest,
        "corpus_sha256": corpus_hash,
    }


def prepare_prompts(
    config: dict[str, Any], models: list[dict], lengths: list[int]
) -> None:
    corpus, corpus_hash = read_corpus(config)
    directory = path_for(config, "prompt_dir")
    directory.mkdir(parents=True, exist_ok=True)
    benchmark = config["benchmark"]
    for model in models:
        destination = prompt_file(config, model)
        existing = json.loads(destination.read_text()) if destination.exists() else []
        selected_targets = set(lengths)
        rows = [row for row in existing if row["target"] not in selected_targets]
        print(f"Sizing prompts for {model['model']}...", flush=True)
        with provider_client(model, benchmark["timeout_seconds"]) as client:
            for target in lengths:
                rows.append(fit_prompt(client, model, benchmark, corpus, corpus_hash, target, False))
                if (
                    target >= benchmark["cached_min_target"]
                    and model.get("cache_api") != "legacy"
                ):
                    rows.append(fit_prompt(client, model, benchmark, corpus, corpus_hash, target, True))
                print(f"  {target:,}", flush=True)
        rows.sort(key=lambda row: (row["target"], row["mode"]))
        destination.write_text(json.dumps(rows, indent=2) + "\n")


def prepared_rows(
    config: dict[str, Any], model: dict[str, Any], lengths: list[int]
) -> list[dict]:
    path = prompt_file(config, model)
    if not path.exists():
        raise ValueError(f"prompts for {model['model']} are missing; run prepare-prompts")
    wanted = set(lengths)
    rows = [row for row in json.loads(path.read_text()) if row["target"] in wanted]
    expected = {(length, "uncached") for length in lengths}
    if model.get("cache_api") != "legacy":
        expected |= {
            (length, "cached")
            for length in lengths
            if length >= config["benchmark"]["cached_min_target"]
        }
    present = {(row["target"], row["mode"]) for row in rows}
    if present != expected:
        raise ValueError("prepared lengths do not match; rerun prepare-prompts")
    return rows


# Streaming and run -----------------------------------------------------------


def sse_events(lines: Any):
    event_name, data = None, []
    for line in lines:
        line = line.rstrip("\r\n")
        if not line:
            if data:
                yield event_name, json.loads("\n".join(data))
            event_name, data = None, []
        elif line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:") and line[5:].strip() != "[DONE]":
            data.append(line[5:].strip())
    if data:
        yield event_name, json.loads("\n".join(data))


def stream_one(
    client: httpx.Client,
    model: dict[str, Any],
    benchmark: dict[str, Any],
    corpus: str,
    row: dict[str, Any],
    cache_key: str | None,
    cache_buster: str | None = None,
    fixed_output: bool = False,
    leading_nonce: bool = False,
) -> dict[str, Any]:
    cached = row["mode"] == "cached"
    instruction = FIXED_OUTPUT_PROMPT if fixed_output else benchmark["prompt"]
    stable, suffix = prompt_parts(
        corpus, row["end"], row["split"], instruction, cached
    )
    suffix = row.get("suffix_override", suffix)
    if cache_buster:
        stable = f"{cache_buster}\n{stable}"
    nonce = " ".join(str(byte % 10) for byte in uuid.uuid4().bytes)
    if leading_nonce:
        suffix = f"Benchmark nonce: {nonce}\n{suffix}"
    else:
        suffix += nonce
    if fixed_output and suffix:
        # prompt_parts normally leaves a nonce label at the end. In the
        # controlled-output experiment, keep the instruction as the final text
        # the model sees while putting request uniqueness before the new input.
        suffix = suffix.removesuffix("\nBenchmark nonce: ")
    messages = blocks(model, stable, suffix, cached)
    if model["provider"] == "openai":
        payload: dict[str, Any] = {
            "model": model["model"],
            "input": messages,
            "max_output_tokens": benchmark["max_output_tokens"],
            "reasoning": {"effort": "none"},
            "service_tier": "default",
            "stream": True,
            "store": False,
        }
        if model.get("cache_api") != "legacy":
            payload["prompt_cache_options"] = {"mode": "explicit"}
        if cache_key:
            payload["prompt_cache_key"] = cache_key
        endpoint = "/v1/responses"
    else:
        payload = {
            "model": model["model"],
            "messages": messages,
            "max_tokens": benchmark["max_output_tokens"],
            "thinking": {"type": model.get("thinking_type", "disabled")},
            "stream": True,
        }
        if model.get("effort"):
            payload["output_config"] = {"effort": model["effort"]}
        endpoint = "/v1/messages"

    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    request = client.build_request(
        "POST", endpoint, content=body, headers={"Content-Type": "application/json"}
    )
    request_started_at = datetime.now(timezone.utc).isoformat()
    started = time.perf_counter_ns()
    result: dict[str, Any] = {
        "request_started_at": request_started_at,
        "request_completed_at": None,
        "headers_ns": None,
        "first_event_ns": None,
        "first_content_ns": None,
        "ttft_ns": None,
        "total_ns": None,
        "status_code": None,
        "request_bytes": len(body),
        "output_preview": "",
        "total_input_tokens": None,
        "new_input_tokens": None,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "output_tokens": None,
        "reasoning_tokens": None if model["provider"] == "openai" else 0,
        "thinking_blocks": 0,
        "requested_service_tier": "default" if model["provider"] == "openai" else None,
        "returned_service_tier": None,
        "error": None,
    }
    response = None
    try:
        response = client.send(request, stream=True)
        result["headers_ns"] = time.perf_counter_ns() - started
        result["status_code"] = response.status_code
        result["request_id"] = response.headers.get("x-request-id") or response.headers.get("request-id")
        result["retry_after"] = response.headers.get("retry-after")
        result["ratelimit_reset_tokens"] = response.headers.get(
            "x-ratelimit-reset-tokens"
        )
        result["ratelimit_remaining_tokens"] = response.headers.get(
            "x-ratelimit-remaining-tokens"
        )
        if response.status_code >= 400:
            result["error"] = response.read()[:4000].decode("utf-8", "replace")
            return result
        for event_name, event in sse_events(response.iter_lines()):
            now = time.perf_counter_ns() - started
            result["first_event_ns"] = result["first_event_ns"] or now
            event_type = event.get("type") or event_name
            if model["provider"] == "openai":
                if event_type in ("response.output_item.added", "response.content_part.added"):
                    result["first_content_ns"] = result["first_content_ns"] or now
                elif event_type == "response.output_text.delta" and event.get("delta"):
                    result["ttft_ns"] = result["ttft_ns"] or now
                    result["output_preview"] += event["delta"]
                elif event_type in ("response.completed", "response.incomplete"):
                    completed = event.get("response", event)
                    result["response_id"] = completed.get("id")
                    result["returned_model"] = completed.get("model")
                    result["returned_service_tier"] = completed.get("service_tier")
                    usage = completed.get("usage") or {}
                    details = usage.get("input_tokens_details") or {}
                    output_details = usage.get("output_tokens_details") or {}
                    total = usage.get("input_tokens")
                    read = details.get("cached_tokens", 0)
                    write = details.get("cache_write_tokens", usage.get("cache_write_tokens", 0))
                    result.update(
                        total_input_tokens=total,
                        new_input_tokens=None if total is None else total - read - write,
                        cache_read_tokens=read,
                        cache_write_tokens=write,
                        output_tokens=usage.get("output_tokens"),
                        reasoning_tokens=output_details.get("reasoning_tokens"),
                    )
                elif event_type in ("error", "response.failed"):
                    result["error"] = str(event.get("error", event))
            else:
                if event_type == "message_start":
                    message = event.get("message", {})
                    result["response_id"] = message.get("id")
                    result["returned_model"] = message.get("model")
                    _anthropic_usage(result, message.get("usage") or {})
                elif event_type == "content_block_start":
                    result["first_content_ns"] = result["first_content_ns"] or now
                    block_type = (event.get("content_block") or {}).get("type")
                    if block_type in ("thinking", "redacted_thinking"):
                        result["thinking_blocks"] += 1
                elif event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    text = delta.get("text", "") if delta.get("type") == "text_delta" else ""
                    if text:
                        result["ttft_ns"] = result["ttft_ns"] or now
                        result["output_preview"] += text
                elif event_type == "message_delta":
                    _anthropic_usage(result, event.get("usage") or {})
                elif event_type == "error":
                    result["error"] = str(event.get("error", event))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        result["total_ns"] = time.perf_counter_ns() - started
        result["request_completed_at"] = datetime.now(timezone.utc).isoformat()
        if response is not None:
            response.close()
    result["output_preview"] = result["output_preview"][:160]
    return result


def _anthropic_usage(result: dict[str, Any], usage: dict[str, Any]) -> None:
    if "input_tokens" in usage:
        result["new_input_tokens"] = usage["input_tokens"]
    result["cache_read_tokens"] = usage.get(
        "cache_read_input_tokens", result["cache_read_tokens"]
    )
    result["cache_write_tokens"] = usage.get(
        "cache_creation_input_tokens", result["cache_write_tokens"]
    )
    result["output_tokens"] = usage.get("output_tokens", result["output_tokens"])
    if result["new_input_tokens"] is not None:
        result["total_input_tokens"] = (
            result["new_input_tokens"]
            + result["cache_read_tokens"]
            + result["cache_write_tokens"]
        )


def request_cost(model: dict[str, Any], result: dict[str, Any]) -> float | None:
    if result["total_input_tokens"] is None:
        return None
    total = result["total_input_tokens"]
    long = model["long_context_threshold"] and total > model["long_context_threshold"]
    input_multiplier = model["long_input_multiplier"] if long else 1
    output_multiplier = model["long_output_multiplier"] if long else 1
    values = (
        (result["new_input_tokens"] or 0) * model["input_usd_per_mtok"],
        result["cache_read_tokens"] * model["cache_read_usd_per_mtok"],
        result["cache_write_tokens"] * model["cache_write_usd_per_mtok"],
    )
    output = (result["output_tokens"] or 0) * model["output_usd_per_mtok"]
    return (sum(values) * input_multiplier + output * output_multiplier) / 1_000_000


def validate_shared_cache_setup(
    model: dict[str, Any], result: dict[str, Any], requested_prefix: int
) -> int:
    prefix = result["cache_read_tokens"] + result["cache_write_tokens"]
    if (
        result["error"]
        or result["total_input_tokens"] is None
        or prefix < requested_prefix
        or prefix - requested_prefix > CACHE_COUNT_TOLERANCE
    ):
        raise RuntimeError(
            f"shared cache setup failed for {model['model']}: "
            f"new={result['new_input_tokens']}, read={result['cache_read_tokens']}, "
            f"write={result['cache_write_tokens']}, error={result['error']}"
        )
    return prefix


def validate_shared_cache_hit(
    model: dict[str, Any],
    result: dict[str, Any],
    requested_prefix: int,
    expected_prefix: int,
    expected_total: int,
) -> None:
    actual_total = result["total_input_tokens"]
    accounting_total = (
        (result["new_input_tokens"] or 0)
        + result["cache_read_tokens"]
        + result["cache_write_tokens"]
    )
    if (
        result["error"]
        or result["ttft_ns"] is None
        or actual_total is None
        or result["cache_read_tokens"] < requested_prefix
        or abs(result["cache_read_tokens"] - expected_prefix) > CACHE_COUNT_TOLERANCE
        or result["cache_write_tokens"] != 0
        or abs(actual_total - expected_total) > CACHE_COUNT_TOLERANCE
        or accounting_total != actual_total
    ):
        raise RuntimeError(
            f"shared cache split mismatch for {model['model']} at {expected_total:,}: "
            f"new={result['new_input_tokens']}, read={result['cache_read_tokens']}, "
            f"write={result['cache_write_tokens']}, total={actual_total}, "
            f"error={result['error']}"
        )


def randomized_blocks(
    rows: list[dict[str, Any]],
    repetitions: int,
    repetitions_by_length: dict[int, int] | None,
    rng: random.Random,
) -> list[tuple[dict[str, Any], int]]:
    """Randomize within rounds while preventing a length from repeating early."""
    counts = {
        row["target"]: (repetitions_by_length or {}).get(row["target"], repetitions)
        for row in rows
    }
    schedule = []
    for repetition in range(max(counts.values())):
        block = [
            (row, repetition)
            for row in rows
            if repetition < counts[row["target"]]
        ]
        rng.shuffle(block)
        schedule.extend(block)
    return schedule


def archived_schedule(
    rows: list[dict[str, Any]], schedule_path: Path
) -> list[tuple[dict[str, Any], int]]:
    """Load an observed target/block order exported with the public dataset."""
    by_target = {row["target"]: row for row in rows}
    with schedule_path.open(newline="", encoding="utf-8") as handle:
        records = list(csv.DictReader(handle))
    schedule = []
    seen = set()
    for record in records:
        target = int(record["target_tokens"])
        repetition = int(record["block"]) - 1
        if target not in by_target:
            raise ValueError(f"schedule contains unprepared target {target:,}")
        key = (target, repetition)
        if key in seen:
            raise ValueError(f"schedule repeats target/block {key}")
        seen.add(key)
        schedule.append((by_target[target], repetition))
    if not schedule:
        raise ValueError("schedule is empty")
    return schedule


def run_benchmark(
    config: dict[str, Any],
    models: list[dict],
    lengths: list[int],
    repetitions: int,
    label: str | None,
    network_label: str | None,
    reuse_cache_session: str | None = None,
    uncached_only: bool = False,
    cold_write_only: bool = False,
    repetitions_by_length: dict[int, int] | None = None,
    skip_warmup: bool = False,
    cached_hit_suffix_tokens: int | None = None,
    shared_cache_prefix_tokens: int | None = None,
    shared_cache_min_interval_seconds: float = 4.0,
    fixed_output: bool = False,
    leading_nonce: bool = False,
    schedule_file: Path | None = None,
) -> Path:
    benchmark = config["benchmark"]
    corpus, corpus_hash = read_corpus(config)
    session = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    output = path_for(config, "results_dir") / f"{session}.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(benchmark["seed"] ^ int(session[-8:], 16))
    failed_attempts = 0
    missing_measurements = 0
    stopped_for_limit = False
    with output.open("a", encoding="utf-8") as handle:
        append_jsonl(
            handle,
            {
                "type": "session",
                "schema_version": RESULT_SCHEMA_VERSION,
                "session": session,
                "label": label,
                "network_label": network_label,
                "timestamp": datetime.now().astimezone().isoformat(),
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "lengths": lengths,
                "repetitions": repetitions,
                "reuse_cache_session": reuse_cache_session,
                "uncached_only": uncached_only,
                "cold_write_only": cold_write_only,
                "repetitions_by_length": repetitions_by_length,
                "skip_warmup": skip_warmup,
                "cached_hit_suffix_tokens": cached_hit_suffix_tokens,
                "shared_cache_prefix_tokens": shared_cache_prefix_tokens,
                "shared_cache_min_interval_seconds": shared_cache_min_interval_seconds,
                "fixed_output": fixed_output,
                "leading_nonce": leading_nonce,
                "schedule_file": str(schedule_file) if schedule_file else None,
                "corpus_sha256": corpus_hash,
            },
        )
        for model in models:
            rows = prepared_rows(config, model, lengths)
            uncached = [row for row in rows if row["mode"] == "uncached"]
            cached = sorted(
                (row for row in rows if row["mode"] == "cached"), key=lambda row: row["target"]
            )
            with provider_client(model, benchmark["timeout_seconds"]) as client:
                # One connection warm-up, excluded from analysis.
                warmup = min(uncached, key=lambda row: row["target"])
                if warmup["target"] > 10_000:
                    try:
                        warmup = next(
                            row for row in prepared_rows(config, model, [10_000])
                            if row["mode"] == "uncached"
                        )
                    except ValueError:
                        pass
                if not skip_warmup:
                    write_sample(
                        handle, client, model, benchmark, corpus, warmup,
                        session, "connection_warmup", -1, None,
                    )
                else:
                    # Warm DNS/TCP/TLS without generating output or adding a paid
                    # inference observation to the session.
                    count_tokens(client, model, "", "connection warmup", False)
                if shared_cache_prefix_tokens is not None:
                    shared_cache_key = (
                        f"ttft:shared:{session}:{model['model']}"
                        if model["provider"] == "openai" else None
                    )
                    shared = shared_prefix_rows(
                        client, model, benchmark, corpus, uncached,
                        shared_cache_prefix_tokens,
                    )
                    prime = dict(shared[0])
                    prime["target"] = prime["cache_estimate"]
                    prime["counted"] = prime["cache_estimate"]
                    prime["new_estimate"] = 0
                    prime["suffix_override"] = ""
                    setup = write_sample_resilient(
                        handle, client, model, benchmark, corpus, prime,
                        session, "cache_setup", -1, shared_cache_key,
                        fixed_output=fixed_output, leading_nonce=leading_nonce,
                    )
                    failed_attempts += setup.get("retry_attempt", 0) + (
                        0 if setup["valid"] else 1
                    )
                    if not setup["valid"]:
                        missing_measurements += sum(
                            (repetitions_by_length or {}).get(row["target"], repetitions)
                            for row in shared
                        )
                        stopped_for_limit = is_quota_limit(setup)
                        break
                    expected_prefix = validate_shared_cache_setup(
                        model, setup, shared_cache_prefix_tokens
                    )
                    schedule = (
                        archived_schedule(shared, schedule_file)
                        if schedule_file
                        else randomized_blocks(
                            shared, repetitions, repetitions_by_length, rng
                        )
                    )
                    previous_start = time.monotonic()
                    for schedule_index, (row, repetition) in enumerate(schedule):
                        time.sleep(max(
                            0,
                            shared_cache_min_interval_seconds
                            - (time.monotonic() - previous_start),
                        ))
                        previous_start = time.monotonic()
                        hit = write_sample_resilient(
                            handle, client, model, benchmark, corpus, row,
                            session, "measured", repetition, shared_cache_key,
                            fixed_output=fixed_output, leading_nonce=leading_nonce,
                        )
                        failed_attempts += hit.get("retry_attempt", 0) + (
                            0 if hit["valid"] else 1
                        )
                        if not hit["valid"]:
                            missing_measurements += 1
                            if is_quota_limit(hit):
                                stopped_for_limit = True
                                missing_measurements += len(schedule) - schedule_index - 1
                                break
                            continue
                        validate_shared_cache_hit(
                            model, hit, shared_cache_prefix_tokens,
                            expected_prefix, row["counted"],
                        )
                    continue
                if uncached_only:
                    schedule = randomized_blocks(
                        uncached, repetitions, repetitions_by_length, rng
                    )
                    previous_start = None
                    for row, repetition in schedule:
                        if previous_start is not None:
                            time.sleep(max(
                                0,
                                shared_cache_min_interval_seconds
                                - (time.monotonic() - previous_start),
                            ))
                        previous_start = time.monotonic()
                        legacy = model.get("cache_api") == "legacy"
                        result = write_sample(
                            handle, client, model, benchmark, corpus, row,
                            session, "measured", repetition,
                            f"ttft:miss:{uuid.uuid4().hex}" if legacy else None,
                            str(uuid.uuid4().int) if legacy else None,
                            fixed_output=fixed_output, leading_nonce=leading_nonce,
                        )
                        if legacy and result["cache_read_tokens"]:
                            raise RuntimeError(
                                f"unexpected cache hit for {model['model']} at {row['target']:,}"
                            )
                    continue
                if cold_write_only:
                    schedule = [
                        (row, repetition)
                        for row in cached
                        for repetition in range(repetitions)
                    ]
                    rng.shuffle(schedule)
                    for row, repetition in schedule:
                        cache_buster = str(uuid.uuid4().int)
                        cache_key = f"ttft:cold:{uuid.uuid4().hex}"
                        cold = write_sample(
                            handle, client, model, benchmark, corpus, row, session,
                            "cache_prime", repetition, cache_key, cache_buster,
                        )
                        if cold["cache_read_tokens"] or not cold["cache_write_tokens"]:
                            raise RuntimeError(
                                f"expected a fresh cache write for {model['model']} at {row['target']:,}"
                            )
                    continue
                if reuse_cache_session:
                    for row in cached:
                        cache_source_target = row["target"]
                        cache_key = (
                            f"ttft:{hashlib.sha256(f'{reuse_cache_session}:{model['model']}:{cache_source_target}'.encode()).hexdigest()[:24]}"
                            if model["provider"] == "openai"
                            else None
                        )
                        if cached_hit_suffix_tokens is not None:
                            row = shorten_cached_suffix(
                                client, model, benchmark, corpus, row,
                                cached_hit_suffix_tokens,
                            )
                        previous_start = None
                        for repetition in range(repetitions):
                            if previous_start is not None:
                                time.sleep(max(0, 4 - (time.monotonic() - previous_start)))
                            previous_start = time.monotonic()
                            hit = write_sample(
                                handle, client, model, benchmark, corpus, row, session, "measured", repetition, cache_key
                            )
                            suffix_delta = abs(
                                (hit["new_input_tokens"] or 0) - row["new_estimate"]
                            )
                            prefix_delta = abs(
                                hit["cache_read_tokens"] - row["cache_estimate"]
                            )
                            if (
                                hit["cache_write_tokens"]
                                or suffix_delta > 64
                                or prefix_delta > 64
                            ):
                                raise RuntimeError(
                                    f"cache expired or split mismatch for {model['model']} "
                                    f"from {cache_source_target:,}: new={hit['new_input_tokens']}, "
                                    f"read={hit['cache_read_tokens']}, write={hit['cache_write_tokens']}"
                                )
                    continue
                # At cache-eligible lengths, the cold cache-write request is the
                # cold measurement. Avoid paying for a duplicate cache-disabled call.
                standalone_uncached = [
                    row for row in uncached if row["target"] < benchmark["cached_min_target"]
                ]
                rng.shuffle(standalone_uncached)
                for row in standalone_uncached:
                    for repetition in range(repetitions):
                        write_sample(
                            handle, client, model, benchmark, corpus, row, session, "measured", repetition, None
                        )
                for row in cached:
                    cache_key = (
                        f"ttft:{hashlib.sha256(f'{session}:{model['model']}:{row['target']}'.encode()).hexdigest()[:24]}"
                        if model["provider"] == "openai"
                        else None
                    )
                    prime = write_sample(
                        handle, client, model, benchmark, corpus, row, session, "cache_prime", -1, cache_key
                    )
                    if prime["cache_read_tokens"] or not prime["cache_write_tokens"]:
                        raise RuntimeError(f"cache prime failed for {model['model']} at {row['target']:,}")
                    for repetition in range(repetitions):
                        hit = write_sample(
                            handle, client, model, benchmark, corpus, row, session, "measured", repetition, cache_key
                        )
                        suffix_delta = abs(
                            (hit["new_input_tokens"] or 0) - row["new_estimate"]
                        )
                        prefix_delta = abs(
                            hit["cache_read_tokens"] - row["cache_estimate"]
                        )
                        if (
                            hit["cache_write_tokens"]
                            or suffix_delta > 64
                            or prefix_delta > 64
                        ):
                            raise RuntimeError(
                                f"cache split mismatch for {model['model']} at {row['target']:,}: "
                                f"new={hit['new_input_tokens']}, read={hit['cache_read_tokens']}, "
                                f"write={hit['cache_write_tokens']}"
                            )
        append_jsonl(
            handle,
            {
                "type": "session_end",
                "schema_version": RESULT_SCHEMA_VERSION,
                "session": session,
                "status": (
                    "partial_limit" if stopped_for_limit
                    else "complete_with_errors" if missing_measurements
                    else "complete"
                ),
                "failed_attempts": failed_attempts,
                "missing_measurements": missing_measurements,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    return output


def write_sample(
    handle: Any,
    client: httpx.Client,
    model: dict[str, Any],
    benchmark: dict[str, Any],
    corpus: str,
    row: dict[str, Any],
    session: str,
    kind: str,
    repetition: int,
    cache_key: str | None,
    cache_buster: str | None = None,
    fixed_output: bool = False,
    leading_nonce: bool = False,
    raise_on_invalid: bool = True,
    retry_attempt: int = 0,
) -> dict[str, Any]:
    result = stream_one(
        client, model, benchmark, corpus, row, cache_key, cache_buster,
        fixed_output, leading_nonce,
    )
    cached = row["mode"] == "cached"
    legacy_miss = model.get("cache_api") == "legacy" and not cached
    valid = (
        not result["error"]
        and result["ttft_ns"] is not None
        and result["total_input_tokens"] is not None
        and (
            result["reasoning_tokens"] == 0
            if model["provider"] == "openai"
            else (
                result["thinking_blocks"] == 0
                if model.get("thinking_type", "disabled") == "disabled"
                else True
            )
        )
        and ((result["cache_read_tokens"] > 0) if cached and kind == "measured" else True)
        and (
            (result["cache_read_tokens"] == 0 and (legacy_miss or result["cache_write_tokens"] == 0))
            if not cached else True
        )
    )
    record = {
        "type": "sample",
        "schema_version": RESULT_SCHEMA_VERSION,
        "session": session,
        "timestamp": result["request_started_at"],
        "provider": model["provider"],
        "model": model["model"],
        "mode": (
            "automatic_cache_miss" if legacy_miss and kind == "measured"
            else row.get("report_mode", row["mode"])
        ),
        "target_tokens": row["target"],
        "prepared_tokens": row["counted"],
        "prompt_sha256": row["prompt_sha256"],
        "kind": kind,
        "repetition": repetition,
        "cache_buster": cache_buster,
        "cache_key_sha256": (
            hashlib.sha256(cache_key.encode()).hexdigest() if cache_key else None
        ),
        "shared_cache_prefix_requested_tokens": row.get(
            "shared_cache_prefix_requested_tokens"
        ),
        "stable_prefix_sha256": row.get("stable_prefix_sha256"),
        "instruction_mode": "fixed_ok" if fixed_output else "summarize",
        "nonce_position": "new_input_start" if leading_nonce else "end",
        "output_compliant": (
            None if not fixed_output or kind != "measured"
            else result["output_preview"].strip() == "OK"
        ),
        "retry_attempt": retry_attempt,
        "valid": valid,
        **result,
    }
    record["estimated_cost_usd"] = request_cost(model, result)
    append_jsonl(handle, record)
    result["valid"] = valid
    result["retry_attempt"] = retry_attempt
    if not valid and raise_on_invalid:
        raise RuntimeError(
            f"invalid response for {model['model']} at {row['target']:,}: "
            f"reasoning={result['reasoning_tokens']}, "
            f"thinking_blocks={result['thinking_blocks']}, "
            f"read={result['cache_read_tokens']}, write={result['cache_write_tokens']}, "
            f"error={result['error']}"
        )
    if valid:
        print(
            f"{model['model']} {row.get('report_mode', row['mode'])} {row['target']:,} "
            f"run={repetition + 1 if repetition >= 0 else kind} "
            f"ttft={result['ttft_ns'] / 1e9:.3f}s",
            flush=True,
        )
    else:
        print(
            f"{model['model']} {row.get('report_mode', row['mode'])} {row['target']:,} "
            f"run={repetition + 1 if repetition >= 0 else kind} "
            f"attempt={retry_attempt + 1} status={result['status_code']} "
            f"error={result['error']}",
            flush=True,
        )
    return result


def is_quota_limit(result: dict[str, Any]) -> bool:
    error = (result.get("error") or "").lower()
    return result.get("status_code") == 429 and any(
        marker in error
        for marker in (
            "insufficient_quota",
            "billing_hard_limit",
            "billing hard limit",
            "usage limit",
        )
    )


def retry_delay_seconds(result: dict[str, Any], retry_attempt: int) -> float:
    values = (result.get("retry_after"), result.get("ratelimit_reset_tokens"))
    for value in values:
        if value is None:
            continue
        text = str(value).strip().lower()
        try:
            return min(120.0, max(1.0, float(text)))
        except ValueError:
            units = (("ms", 0.001), ("s", 1.0), ("m", 60.0), ("h", 3600.0))
            for suffix, multiplier in units:
                if text.endswith(suffix):
                    try:
                        return min(120.0, max(1.0, float(text[:-len(suffix)]) * multiplier))
                    except ValueError:
                        break
    return min(120.0, 15.0 * (2 ** retry_attempt))


def write_sample_resilient(
    handle: Any,
    client: httpx.Client,
    model: dict[str, Any],
    benchmark: dict[str, Any],
    corpus: str,
    row: dict[str, Any],
    session: str,
    kind: str,
    repetition: int,
    cache_key: str | None,
    cache_buster: str | None = None,
    fixed_output: bool = False,
    leading_nonce: bool = False,
) -> dict[str, Any]:
    result = None
    for retry_attempt in range(SHARED_REQUEST_MAX_ATTEMPTS):
        result = write_sample(
            handle, client, model, benchmark, corpus, row, session, kind,
            repetition, cache_key, cache_buster, fixed_output, leading_nonce,
            raise_on_invalid=False, retry_attempt=retry_attempt,
        )
        if result["valid"] or is_quota_limit(result):
            return result
        status = result.get("status_code")
        if status is not None and status not in TRANSIENT_STATUS_CODES:
            return result
        if retry_attempt + 1 < SHARED_REQUEST_MAX_ATTEMPTS:
            delay = retry_delay_seconds(result, retry_attempt)
            print(
                f"retrying {model['model']} at {row['target']:,} in {delay:.1f}s "
                f"after status={status}",
                flush=True,
            )
            time.sleep(delay)
    assert result is not None
    return result


def append_jsonl(handle: Any, value: dict[str, Any]) -> None:
    handle.write(json.dumps(value, separators=(",", ":")) + "\n")
    handle.flush()
    os.fsync(handle.fileno())


# Cost and analysis -----------------------------------------------------------


def estimate(
    model: dict[str, Any], benchmark: dict[str, Any], lengths: list[int], reps: int,
    reuse_cache: bool = False, uncached_only: bool = False,
    cold_write_only: bool = False,
    repetitions_by_length: dict[int, int] | None = None,
    skip_warmup: bool = False,
    cached_hit_suffix_tokens: int | None = None,
    shared_cache_prefix_tokens: int | None = None,
) -> dict:
    limit = min(
        model["context_window"] - benchmark["max_output_tokens"] - benchmark["context_safety_tokens"],
        model.get("max_input_tokens", model["context_window"]),
    )
    targets = [min(length, limit) for length in lengths]
    warmup_target = min(10_000, min(targets))
    cached = [target for length, target in zip(lengths, targets) if length >= benchmark["cached_min_target"]]
    if shared_cache_prefix_tokens is not None:
        estimated = 0.0 if skip_warmup else estimated_request_cost(
            model, warmup_target, 0, 0, benchmark["max_output_tokens"]
        )
        estimated += estimated_request_cost(
            model, 32, 0, shared_cache_prefix_tokens,
            benchmark["max_output_tokens"],
        )
        request_count = 0
        for length, target in zip(lengths, targets):
            target_reps = (repetitions_by_length or {}).get(length, reps)
            request_count += target_reps
            estimated += target_reps * estimated_request_cost(
                model, target - shared_cache_prefix_tokens,
                shared_cache_prefix_tokens, 0,
                benchmark["max_output_tokens"],
            )
        return {
            "model": model["name"],
            "requests": (0 if skip_warmup else 1) + 1 + request_count,
            "estimated_usd": estimated,
        }
    if uncached_only:
        estimated = 0.0 if skip_warmup else estimated_request_cost(
            model, warmup_target, 0, 0, benchmark["max_output_tokens"]
        )
        estimated += sum(
            (repetitions_by_length or {}).get(length, reps)
            * estimated_request_cost(model, target, 0, 0, benchmark["max_output_tokens"])
            for length, target in zip(lengths, targets)
        )
        requests = (0 if skip_warmup else 1) + sum(
            (repetitions_by_length or {}).get(length, reps) for length in lengths
        )
        return {"model": model["name"], "requests": requests, "estimated_usd": estimated}
    if cold_write_only:
        estimated = estimated_request_cost(
            model, warmup_target, 0, 0, benchmark["max_output_tokens"]
        )
        for target in cached:
            prefix, suffix = target - benchmark["cached_suffix_tokens"], benchmark["cached_suffix_tokens"]
            estimated += reps * estimated_request_cost(
                model, suffix, 0, prefix, benchmark["max_output_tokens"]
            )
        return {"model": model["name"], "requests": 1 + len(cached) * reps, "estimated_usd": estimated}
    if reuse_cache:
        estimated = 0.0 if skip_warmup else estimated_request_cost(
            model, warmup_target, 0, 0, benchmark["max_output_tokens"]
        )
        for target in cached:
            prefix, suffix = target - benchmark["cached_suffix_tokens"], benchmark["cached_suffix_tokens"]
            suffix = cached_hit_suffix_tokens or suffix
            estimated += reps * estimated_request_cost(
                model, suffix, prefix, 0, benchmark["max_output_tokens"]
            )
        return {
            "model": model["name"],
            "requests": (0 if skip_warmup else 1) + len(cached) * reps,
            "estimated_usd": estimated,
        }
    standalone = [target for length, target in zip(lengths, targets) if length < benchmark["cached_min_target"]]
    requests = (0 if skip_warmup else 1) + len(standalone) * reps + len(cached) * (1 + reps)
    estimated = 0.0
    initial = [] if skip_warmup else [warmup_target]
    for target in [*initial, *[value for value in standalone for _ in range(reps)]]:
        estimated += estimated_request_cost(model, target, 0, 0, benchmark["max_output_tokens"])
    for target in cached:
        prefix, suffix = target - benchmark["cached_suffix_tokens"], benchmark["cached_suffix_tokens"]
        estimated += estimated_request_cost(model, suffix, 0, prefix, benchmark["max_output_tokens"])
        estimated += reps * estimated_request_cost(model, suffix, prefix, 0, benchmark["max_output_tokens"])
    return {"model": model["name"], "requests": requests, "estimated_usd": estimated}


def estimated_request_cost(model: dict, new: int, read: int, write: int, output: int) -> float:
    total = new + read + write
    long = model["long_context_threshold"] and total > model["long_context_threshold"]
    input_multiplier = model["long_input_multiplier"] if long else 1
    output_multiplier = model["long_output_multiplier"] if long else 1
    inputs = (
        new * model["input_usd_per_mtok"]
        + read * model["cache_read_usd_per_mtok"]
        + write * model["cache_write_usd_per_mtok"]
    )
    return (inputs * input_multiplier + output * model["output_usd_per_mtok"] * output_multiplier) / 1_000_000


def analyze(files: list[Path], output: Path, config: dict[str, Any]) -> None:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        raise ValueError("install analysis dependencies with: pip install -e '.[analysis]'") from exc
    records = []
    for path in files:
        records.extend(json.loads(line) for line in path.read_text().splitlines() if line)
    session_headers = {
        record["session"]: record
        for record in records
        if record.get("type") == "session"
    }
    completion_records = {
        record["session"]
        for record in records
        if record.get("type") == "session_end" and record.get("status") == "complete"
    }
    completion_required = {
        session
        for session, record in session_headers.items()
        if record.get("schema_version", 1) >= RESULT_SCHEMA_VERSION
    }
    invalid_sessions = {
        record["session"]
        for record in records
        if record.get("type") == "sample" and record.get("valid") is False
    }
    invalid_sessions |= completion_required - completion_records
    configured_models = {
        (model["provider"], model["model"]): model
        for model in config["models"].values()
    }
    for record in records:
        model = configured_models.get((record.get("provider"), record.get("model")))
        if record.get("type") == "sample" and model and record.get("total_input_tokens") is not None:
            record["estimated_cost_usd"] = request_cost(model, record)
    measured = []
    for record in records:
        if record.get("type") != "sample" or record.get("kind") not in ("measured", "cache_prime"):
            continue
        record = dict(record)
        if record["kind"] == "cache_prime":
            record["mode"] = "cold_cache_write"
        measured.append(record)
    frame = pd.DataFrame(measured)
    if frame.empty:
        raise ValueError("no measured samples found")
    timestamp_source = (
        frame["request_started_at"].fillna(frame["timestamp"])
        if "request_started_at" in frame else frame["timestamp"]
    )
    timestamps_utc = pd.to_datetime(timestamp_source, utc=True)
    timestamps_local = timestamps_utc.dt.tz_convert("America/Toronto")
    frame["run_timestamp_utc"] = timestamps_utc.dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    frame["run_timestamp_local"] = timestamps_local.dt.strftime(
        "%Y-%m-%dT%H:%M:%S.%f%z"
    )
    frame["run_local_date"] = timestamps_local.dt.strftime("%Y-%m-%d")
    frame["run_local_hour"] = timestamps_local.dt.hour
    frame["run_local_minute"] = timestamps_local.dt.minute
    frame["run_timezone"] = "America/Toronto"
    frame["ttft_seconds"] = frame["ttft_ns"] / 1e9
    frame["session_complete"] = (
        ~frame["session"].isin(completion_required)
        | frame["session"].isin(completion_records)
    )
    frame["session_valid"] = ~frame["session"].isin(invalid_sessions)
    frame["slow_path"] = False
    cell = ["session", "provider", "model", "mode", "target_tokens"]
    for _, indexes in frame[frame["valid"]].groupby(cell).groups.items():
        values = frame.loc[indexes, "ttft_seconds"].to_numpy()
        median = np.median(values)
        mad = np.median(np.abs(values - median))
        threshold = median + 3 * 1.4826 * mad if mad else np.quantile(values, 0.75) + 1.5 * (np.quantile(values, 0.75) - np.quantile(values, 0.25))
        if threshold == median and max(values) > median:
            threshold = median
        frame.loc[indexes, "slow_path"] = values > threshold
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "samples.csv", index=False)
    frame.to_parquet(output / "samples.parquet", index=False)
    valid = frame[
        frame["valid"] & frame["session_valid"] & frame["ttft_seconds"].notna()
    ]
    group = ["provider", "model", "mode", "target_tokens"]
    summary = valid.groupby(group, as_index=False).agg(
        samples=("ttft_seconds", "count"),
        median_seconds=("ttft_seconds", "median"),
        q1_seconds=("ttft_seconds", lambda value: value.quantile(0.25)),
        q3_seconds=("ttft_seconds", lambda value: value.quantile(0.75)),
        p95_seconds=("ttft_seconds", lambda value: value.quantile(0.95)),
        max_seconds=("ttft_seconds", "max"),
        slow_path_rate=("slow_path", "mean"),
        mean_input_tokens=("total_input_tokens", "mean"),
        cost_usd=("estimated_cost_usd", "sum"),
    )
    summary.to_csv(output / "summary.csv", index=False)
    fits = []
    for key, data in summary.groupby(["provider", "model", "mode"]):
        if len(data) < 3:
            continue
        x, y = data["mean_input_tokens"].to_numpy() / 1e6, data["median_seconds"].to_numpy()
        for degree in (1, 2):
            coefficients = np.polyfit(x, y, degree)
            prediction = np.polyval(coefficients, x)
            fits.append(
                {
                    "provider": key[0],
                    "model": key[1],
                    "mode": key[2],
                    "degree": degree,
                    "coefficients": coefficients.tolist(),
                    "rmse_seconds": float(np.sqrt(np.mean((prediction - y) ** 2))),
                }
            )
        samples = valid[(valid["provider"] == key[0]) & (valid["model"] == key[1]) & (valid["mode"] == key[2])]
        figure, axis = plt.subplots(figsize=(8, 5))
        axis.scatter(samples["total_input_tokens"], samples["ttft_seconds"], alpha=0.45)
        axis.plot(data["mean_input_tokens"], data["median_seconds"], color="black", label="median")
        axis.plot(data["mean_input_tokens"], data["p95_seconds"], linestyle="--", label="p95")
        axis.set_xscale("log")
        axis.set(xlabel="Input tokens", ylabel="TTFT (seconds)", title=f"{key[1]} — {key[2]}")
        axis.grid(alpha=0.2)
        axis.legend()
        figure.tight_layout()
        figure.savefig(output / f"{key[0]}__{key[1]}__{key[2]}.png", dpi=160)
        plt.close(figure)

    styles = {
        "uncached": ("Strict uncached", "#d95f02", "o"),
        "automatic_cache_miss": ("Automatic-cache miss", "#e7298a", "^"),
        "cached": ("Cached hit", "#1b9e77", "s"),
        "shared_prefix_cached": ("Shared-prefix cache hit", "#1f78b4", "P"),
        "cold_cache_write": ("Cold cache write", "#7570b3", "D"),
    }
    for (provider, model), samples in valid.groupby(["provider", "model"]):
        figure, axis = plt.subplots(figsize=(9, 6))
        slow_label_added = False
        for mode in (
            "uncached", "automatic_cache_miss", "cached",
            "shared_prefix_cached", "cold_cache_write",
        ):
            data = samples[samples["mode"] == mode]
            if data.empty:
                continue
            label, color, marker = styles[mode]
            jittered_x, plotted_y = [], []
            for _, cell_data in data.groupby("target_tokens"):
                offsets = (
                    np.array([0.0]) if len(cell_data) == 1
                    else np.linspace(-0.018, 0.018, len(cell_data))
                )
                jittered_x.extend(cell_data["total_input_tokens"].to_numpy() * (10 ** offsets))
                plotted_y.extend(cell_data["ttft_seconds"].to_numpy())
            axis.scatter(
                jittered_x, plotted_y, s=42, alpha=0.6, color=color,
                marker=marker, label=f"{label} (samples + median)", zorder=2,
            )
            medians = summary[
                (summary["provider"] == provider)
                & (summary["model"] == model)
                & (summary["mode"] == mode)
            ].sort_values("mean_input_tokens")
            axis.plot(
                medians["mean_input_tokens"], medians["median_seconds"],
                color=color, marker=marker, linewidth=2.2, markersize=6, zorder=3,
            )
            slow = data[data["slow_path"]]
            if not slow.empty:
                axis.scatter(
                    slow["total_input_tokens"], slow["ttft_seconds"],
                    s=95, facecolors="none", edgecolors="#c62828", linewidths=1.4,
                    label="Flagged slow path" if not slow_label_added else None, zorder=4,
                )
                slow_label_added = True
        axis.set_xscale("log")
        axis.set_yscale("log")
        ticks = sorted(samples["target_tokens"].unique())
        axis.set_xticks(
            ticks, [f"{value / 1000:g}k" for value in ticks],
            rotation=35, ha="right", fontsize=8,
        )
        threshold = configured_models[(provider, model)]["long_context_threshold"]
        if threshold:
            axis.axvline(
                threshold, color="#555555", linestyle=":", linewidth=1.4,
                label=f"{threshold / 1000:g}k pricing threshold", zorder=1,
            )
        axis.set(
            xlabel="Input tokens (log scale)",
            ylabel="TTFT in seconds (log scale)",
            title=f"{model} TTFT — all measured samples",
        )
        axis.grid(which="both", alpha=0.2)
        axis.legend()
        figure.tight_layout()
        figure.savefig(output / f"{provider}__{model}__all_loglog.png", dpi=180)
        plt.close(figure)
    (output / "fits.json").write_text(json.dumps(fits, indent=2) + "\n")


# CLI ------------------------------------------------------------------------


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="ttft-bench")
    root.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    commands = root.add_subparsers(dest="command", required=True)
    corpus = commands.add_parser("prepare-corpus")
    corpus.add_argument("--force", action="store_true")
    prompts = commands.add_parser("prepare-prompts")
    selection_args(prompts)
    cost = commands.add_parser("estimate")
    selection_args(cost)
    cost.add_argument("--repetitions", type=int)
    cost.add_argument("--repetitions-by-length", help="TOKEN:COUNT comma-separated")
    cost.add_argument("--shared-cache-prefix-tokens", type=int)
    cost.add_argument("--skip-warmup", action="store_true")
    run = commands.add_parser("run")
    selection_args(run)
    run.add_argument("--repetitions", type=int)
    run.add_argument("--repetitions-by-length", help="TOKEN:COUNT comma-separated")
    run.add_argument("--label")
    run.add_argument("--network-label")
    run.add_argument("--reuse-cache-session")
    run.add_argument("--cached-hit-suffix-tokens", type=int)
    run.add_argument("--shared-cache-prefix-tokens", type=int)
    run.add_argument("--shared-cache-min-interval-seconds", type=float, default=4.0)
    run.add_argument("--uncached-only", action="store_true")
    run.add_argument("--cold-write-only", action="store_true")
    run.add_argument("--skip-warmup", action="store_true")
    run.add_argument("--fixed-output", action="store_true")
    run.add_argument("--leading-nonce", action="store_true")
    run.add_argument("--schedule-file", type=Path)
    run.add_argument("--max-cost-usd", type=float, default=100)
    run.add_argument("--yes", action="store_true")
    report = commands.add_parser("analyze")
    report.add_argument("results", nargs="+", type=Path)
    report.add_argument("--output", type=Path, default=ROOT / "reports")
    return root


def selection_args(command: argparse.ArgumentParser) -> None:
    command.add_argument("--models", help="comma-separated config names")
    command.add_argument("--lengths", help="comma-separated token counts")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    config = load_config(args.config)
    load_dotenv(config["root"] / ".env", override=False)
    try:
        if args.command == "prepare-corpus":
            print(prepare_corpus(config, args.force))
        elif args.command == "analyze":
            analyze(args.results, args.output, config)
            print(args.output)
        else:
            models, lengths = selected(args, config)
            if args.command == "prepare-prompts":
                prepare_prompts(config, models, lengths)
            else:
                repetitions = args.repetitions or config["benchmark"]["repetitions"]
                reuse_cache = args.command == "run" and bool(args.reuse_cache_session)
                uncached_only = args.command == "run" and args.uncached_only
                cold_write_only = args.command == "run" and args.cold_write_only
                skip_warmup = bool(getattr(args, "skip_warmup", False))
                fixed_output = bool(getattr(args, "fixed_output", False))
                leading_nonce = bool(getattr(args, "leading_nonce", False))
                schedule_file = getattr(args, "schedule_file", None)
                cached_hit_suffix_tokens = (
                    args.cached_hit_suffix_tokens if args.command == "run" else None
                )
                shared_cache_prefix_tokens = getattr(
                    args, "shared_cache_prefix_tokens", None
                )
                repetitions_by_length = (
                    repetition_map(getattr(args, "repetitions_by_length", None))
                )
                if sum(map(bool, (
                    reuse_cache, uncached_only, cold_write_only,
                    shared_cache_prefix_tokens is not None,
                ))) > 1:
                    raise ValueError("cache reuse, uncached-only, and cold-write-only modes cannot be combined")
                if repetitions_by_length and not (
                    uncached_only or shared_cache_prefix_tokens is not None
                ):
                    raise ValueError(
                        "--repetitions-by-length requires --uncached-only or "
                        "--shared-cache-prefix-tokens"
                    )
                if repetitions_by_length and set(repetitions_by_length) != set(lengths):
                    raise ValueError("--repetitions-by-length must specify every selected length")
                if cached_hit_suffix_tokens is not None and not reuse_cache:
                    raise ValueError("--cached-hit-suffix-tokens requires --reuse-cache-session")
                if shared_cache_prefix_tokens is not None and shared_cache_prefix_tokens < 1024:
                    raise ValueError("shared cache prefix must be at least 1,024 tokens")
                if (
                    shared_cache_prefix_tokens is not None
                    and shared_cache_prefix_tokens >= min(lengths)
                ):
                    raise ValueError("shared cache prefix must be smaller than every target length")
                if shared_cache_prefix_tokens is not None and any(
                    model.get("cache_api") == "legacy" for model in models
                ):
                    raise ValueError(
                        "shared-prefix mode requires explicit caching and does not "
                        "support legacy OpenAI models"
                    )
                shared_cache_min_interval_seconds = getattr(
                    args, "shared_cache_min_interval_seconds", 4.0
                )
                if shared_cache_min_interval_seconds < 0:
                    raise ValueError("shared-cache interval cannot be negative")
                if schedule_file and (
                    shared_cache_prefix_tokens is None or len(models) != 1
                ):
                    raise ValueError(
                        "--schedule-file requires shared-prefix mode and exactly one model"
                    )
                estimates = [
                    estimate(
                        model, config["benchmark"], lengths, repetitions,
                        reuse_cache, uncached_only, cold_write_only,
                        repetitions_by_length, skip_warmup,
                        cached_hit_suffix_tokens,
                        shared_cache_prefix_tokens,
                    )
                    for model in models
                ]
                for item in estimates:
                    print(f"{item['model']}: {item['requests']} requests, about ${item['estimated_usd']:.2f}")
                if args.command == "run":
                    total = sum(item["estimated_usd"] for item in estimates)
                    if total > args.max_cost_usd and not args.yes:
                        raise ValueError(
                            f"estimate ${total:.2f} exceeds ${args.max_cost_usd:.2f}; rerun with --yes"
                        )
                    print(
                        run_benchmark(
                            config, models, lengths, repetitions, args.label, args.network_label,
                            args.reuse_cache_session, args.uncached_only,
                            args.cold_write_only,
                            repetitions_by_length,
                            args.skip_warmup,
                            cached_hit_suffix_tokens,
                            shared_cache_prefix_tokens,
                            shared_cache_min_interval_seconds,
                            fixed_output,
                            leading_nonce,
                            schedule_file,
                        )
                    )
        return 0
    except (OSError, ValueError, RuntimeError, httpx.HTTPError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
