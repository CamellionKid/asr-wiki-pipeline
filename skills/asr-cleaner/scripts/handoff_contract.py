#!/usr/bin/env python3
"""Create and validate the asr-cleaner -> asr-life-log handoff manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
INPUT_TYPES = {"raw_transcript"}
CLEANING_STATUSES = {"completed", "completed_with_uncertainty"}
ARCHIVE_SUCCESS_STATUSES = {"completed", "noop"}
SENSITIVE_DATA_TYPES = {"none", "candidate", "employee", "other"}


class ContractError(ValueError):
    """Raised when a handoff manifest violates the pipeline contract."""


def require_file(value: str | Path | None, label: str) -> Path:
    if value is None or not str(value).strip():
        raise ContractError(f"{label} is missing")
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ContractError(f"{label} does not exist or is not a file: {path}")
    return path


def parse_record_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ContractError(f"record_date must use YYYY-MM-DD: {value}") from exc
    return parsed.isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=".handoff-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def load_manifest(path_value: str | Path) -> tuple[Path, dict[str, Any]]:
    path = require_file(path_value, "manifest")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ContractError(f"manifest is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ContractError("manifest root must be a JSON object")
    return path, payload


def manifest_output(
    payload: dict[str, Any], path: Path, **extra: Any
) -> dict[str, Any]:
    return {
        "pipeline_id": payload.get("pipeline_id"),
        "manifest_path": str(path),
        **extra,
    }


def create_manifest(args: argparse.Namespace) -> dict[str, Any]:
    source = require_file(args.source_path, "source_path")
    record_date = parse_record_date(args.record_date)
    source_digest = sha256_file(source)
    pipeline_id = f"asr-{record_date.replace('-', '')}-{source_digest[:12]}"
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else Path("/tmp/asr-life-log") / pipeline_id / "handoff.json"
    )

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "pipeline_id": pipeline_id,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "record_date": record_date,
        "source": {
            "type": args.input_type,
            "path": str(source),
            "sha256": source_digest,
            "language": args.language,
        },
        "transcription": {
            "status": "provided",
            "transcript_path": str(source),
        },
        "cleaning": {
            "status": "pending",
            "cleaned_text_path": None,
            "report_path": None,
            "pending_items": [],
            "category_hints": [],
        },
        "safety": {
            "sensitive_data": "unknown",
            "archive_confirmed": False,
        },
        "archive": {
            "requested": not args.no_archive,
            "status": "pending" if not args.no_archive else "skipped",
            "target_path": None,
            "daily_log_path": None,
        },
    }

    if output_path.exists():
        _, existing = load_manifest(output_path)
        if (
            existing.get("pipeline_id") != pipeline_id
            or existing.get("source", {}).get("sha256") != source_digest
        ):
            raise ContractError(
                f"refusing to overwrite a different manifest: {output_path}"
            )
        return manifest_output(existing, output_path, created=False)

    atomic_write_json(output_path, payload)
    return manifest_output(payload, output_path, created=True)


def mark_cleaned(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path, payload = load_manifest(args.manifest)
    source_type = payload.get("source", {}).get("type")
    if source_type not in INPUT_TYPES:
        raise ContractError(f"unsupported source type in manifest: {source_type}")
    cleaned_text = require_file(args.cleaned_text_path, "cleaned_text_path")
    report = require_file(args.report_path, "report_path")
    transcript = require_file(
        payload.get("transcription", {}).get("transcript_path"),
        "transcription.transcript_path",
    )
    payload["transcription"] = {
        "status": "provided",
        "transcript_path": str(transcript),
    }

    pending_items = list(dict.fromkeys(args.pending_item or []))
    category_hints = list(dict.fromkeys(args.category_hint or []))
    has_uncertainty = bool(pending_items)
    payload["cleaning"] = {
        "status": "completed_with_uncertainty" if has_uncertainty else "completed",
        "cleaned_text_path": str(cleaned_text),
        "report_path": str(report),
        "pending_items": pending_items,
        "category_hints": category_hints,
    }
    payload["safety"] = {
        "sensitive_data": args.sensitive_data,
        "archive_confirmed": bool(args.archive_confirmed),
    }

    atomic_write_json(manifest_path, payload)
    return manifest_output(
        payload, manifest_path, cleaning_status=payload["cleaning"]["status"]
    )


def validate_manifest(payload: dict[str, Any], stage: str) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must equal {SCHEMA_VERSION}")
    pipeline_id = payload.get("pipeline_id")
    if not isinstance(pipeline_id, str) or not pipeline_id.startswith("asr-"):
        errors.append("pipeline_id is missing or invalid")
    try:
        parse_record_date(str(payload.get("record_date", "")))
    except ContractError as exc:
        errors.append(str(exc))

    source = payload.get("source")
    if not isinstance(source, dict) or source.get("type") not in INPUT_TYPES:
        errors.append("source.type is missing or unsupported")
    else:
        try:
            source_path = require_file(source.get("path", ""), "source.path")
            if source.get("sha256") != sha256_file(source_path):
                errors.append("source.sha256 does not match the current source file")
        except ContractError as exc:
            errors.append(str(exc))

    transcription = payload.get("transcription", {})
    if transcription.get("status") != "provided":
        errors.append("raw transcript input requires transcription.status=provided")
    try:
        require_file(
            transcription.get("transcript_path", ""), "transcription.transcript_path"
        )
    except ContractError as exc:
        errors.append(str(exc))
    cleaning = payload.get("cleaning", {})
    if cleaning.get("status") not in CLEANING_STATUSES:
        errors.append("cleaning.status is not ready for life-log")
    for key in ("cleaned_text_path", "report_path"):
        try:
            require_file(cleaning.get(key, ""), f"cleaning.{key}")
        except ContractError as exc:
            errors.append(str(exc))

    safety = payload.get("safety", {})
    sensitive_data = safety.get("sensitive_data")
    if sensitive_data not in SENSITIVE_DATA_TYPES:
        errors.append("safety.sensitive_data must be inspected before archival")
    elif sensitive_data != "none" and not safety.get("archive_confirmed"):
        errors.append("sensitive personal data requires explicit archival confirmation")

    archive = payload.get("archive", {})
    if not archive.get("requested"):
        errors.append("archive.requested is false; do not call asr-life-log")

    if stage == "after-life-log":
        if archive.get("status") not in ARCHIVE_SUCCESS_STATUSES:
            errors.append("archive.status must be completed or noop")
        target_path: Path | None = None
        daily_log_path: Path | None = None
        try:
            target_path = require_file(
                archive.get("target_path", ""), "archive.target_path"
            )
        except ContractError as exc:
            errors.append(str(exc))
        try:
            daily_log_path = require_file(
                archive.get("daily_log_path", ""), "archive.daily_log_path"
            )
        except ContractError as exc:
            errors.append(str(exc))
        if target_path and pipeline_id:
            marker = f"%% asr-pipeline:{pipeline_id} %%"
            if marker not in target_path.read_text(encoding="utf-8"):
                errors.append("archive target does not contain the pipeline marker")
        if target_path and daily_log_path:
            expected_link = f"[[{target_path.stem}"
            if expected_link not in daily_log_path.read_text(encoding="utf-8"):
                errors.append(
                    "Daily Log does not contain a link to the life-log target"
                )

    return errors


def validate_command(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    manifest_path, payload = load_manifest(args.manifest)
    errors = validate_manifest(payload, args.stage)
    result = manifest_output(
        payload,
        manifest_path,
        stage=args.stage,
        valid=not errors,
        errors=errors,
    )
    return result, 0 if not errors else 1


def complete_archive(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path, payload = load_manifest(args.manifest)
    archive = payload.setdefault("archive", {})
    archive["status"] = args.status
    archive["target_path"] = (
        str(Path(args.target_path).expanduser().resolve()) if args.target_path else None
    )
    archive["daily_log_path"] = (
        str(Path(args.daily_log_path).expanduser().resolve())
        if args.daily_log_path
        else None
    )
    atomic_write_json(manifest_path, payload)
    return manifest_output(payload, manifest_path, archive_status=args.status)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser(
        "create", help="Create an idempotent handoff manifest"
    )
    create.add_argument("--input-type", choices=sorted(INPUT_TYPES), required=True)
    create.add_argument("--source-path", required=True)
    create.add_argument("--record-date", required=True)
    create.add_argument("--language", default="auto")
    create.add_argument("--no-archive", action="store_true")
    create.add_argument("--output")
    create.set_defaults(handler=create_manifest)

    cleaned = subparsers.add_parser("mark-cleaned", help="Register cleaning artifacts")
    cleaned.add_argument("--manifest", required=True)
    cleaned.add_argument("--cleaned-text-path", required=True)
    cleaned.add_argument("--report-path", required=True)
    cleaned.add_argument("--pending-item", action="append")
    cleaned.add_argument("--category-hint", action="append")
    cleaned.add_argument(
        "--sensitive-data", choices=sorted(SENSITIVE_DATA_TYPES), required=True
    )
    cleaned.add_argument("--archive-confirmed", action="store_true")
    cleaned.set_defaults(handler=mark_cleaned)

    validate = subparsers.add_parser("validate", help="Validate a lifecycle gate")
    validate.add_argument("--manifest", required=True)
    validate.add_argument(
        "--stage", choices=["before-life-log", "after-life-log"], required=True
    )
    validate.set_defaults(handler=validate_command)

    complete = subparsers.add_parser(
        "complete", help="Record the downstream archive result"
    )
    complete.add_argument("--manifest", required=True)
    complete.add_argument(
        "--status", choices=["completed", "noop", "blocked", "failed"], required=True
    )
    complete.add_argument("--target-path")
    complete.add_argument("--daily-log-path")
    complete.set_defaults(handler=complete_archive)

    return parser


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = args.handler(args)
        if isinstance(result, tuple):
            payload, exit_code = result
        else:
            payload, exit_code = result, 0
        emit(payload)
        return exit_code
    except (ContractError, OSError) as exc:
        emit({"valid": False, "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
