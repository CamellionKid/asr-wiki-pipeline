#!/usr/bin/env python3
"""Validate an ASR Wiki pack against asr-pipeline completeness gates."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"〔|TODO|待补")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---", re.S)
NUMBERED_NAME_RE = re.compile(r"^(\d{2}) ")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。？！])")
ANNOTATION_ONLY_RE = re.compile(r"^\[.*?\]$")
REQUIRED_ALL = ("type", "date", "domain", "pipeline_id")
REQUIRED_NUMBERED = REQUIRED_ALL + ("source",)


def nw(text: str) -> str:
    return re.sub(r"\s+", "", text)


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.strip().startswith("-") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.startswith(" "):
            continue
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def pack_files(pack_dir: Path) -> list[Path]:
    return sorted(p for p in pack_dir.glob("*.md") if p.is_file())


def find_map(files: list[Path]) -> Path | None:
    maps = [p for p in files if "文档地图" in p.name and not NUMBERED_NAME_RE.match(p.name)]
    if len(maps) == 1:
        return maps[0]
    return None


def find_01(files: list[Path]) -> Path | None:
    ones = [p for p in files if p.name.startswith("01 ")]
    return ones[0] if len(ones) == 1 else None


def check_numbering(files: list[Path]) -> tuple[bool, str]:
    numbered: list[int] = []
    for path in files:
        match = NUMBERED_NAME_RE.match(path.name)
        if match:
            numbered.append(int(match.group(1)))
        elif "文档地图" not in path.name:
            return False, f"non-numbered extra file: {path.name}"
    if not numbered:
        return False, "no numbered files"
    numbered.sort()
    expected = list(range(1, numbered[-1] + 1))
    if numbered != expected:
        return False, f"got {numbered}, expected {expected}"
    forbidden = [p.name for p in files if p.name.startswith("00 ")]
    if forbidden:
        return False, f"forbidden numbered map: {forbidden}"
    map_file = find_map(files)
    if map_file is None:
        return False, "missing unsuffixed <活动名>｜文档地图.md"
    if "｜文档地图" not in map_file.name:
        return False, f"map name missing activity prefix: {map_file.name}"
    return True, f"01–{numbered[-1]:02d} consecutive; map {map_file.name}"


def check_01_role(path: Path | None) -> tuple[bool, str]:
    if path is None:
        return False, "missing 01 file"
    name = path.name
    qa = "一问一答" in name
    full = "全文转写" in name
    if qa == full:
        return False, f"01 role must be 一问一答 or 全文转写, got {name}"
    meta = parse_frontmatter(path.read_text(encoding="utf-8"))
    mode = meta.get("transcript_mode", "")
    expected = "qa" if qa else "full"
    ntype = meta.get("type", "")
    if mode == expected:
        return True, f"{name}; transcript_mode={mode}"
    if qa and ntype == "interview-qa" and mode in ("", "qa"):
        return True, f"{name}; type=interview-qa (implicit qa)"
    return False, f"transcript_mode={mode!r} type={ntype!r} expected {expected}"


def iter_sentences(text: str) -> list[str]:
    start = text.find("[说话人")
    body = text[start:] if start >= 0 else text
    out: list[str] = []
    for sent in SENTENCE_SPLIT_RE.split(body):
        sent = sent.strip()
        compact = nw(sent)
        if len(compact) < 12:
            continue
        if ANNOTATION_ONLY_RE.fullmatch(compact):
            continue
        if compact.startswith("[推测修复") or compact.startswith("[名词待确认"):
            continue
        out.append(sent)
    return out


def quote_text(text: str) -> str:
    return "\n".join(re.findall(r"^> ?(.*)$", text, re.M))


def check_coverage(qa_path: Path, cleaned_path: Path) -> tuple[bool, str]:
    cleaned = cleaned_path.read_text(encoding="utf-8")
    qa = qa_path.read_text(encoding="utf-8")
    if FRONTMATTER_RE.match(cleaned):
        cleaned_body = FRONTMATTER_RE.sub("", cleaned, count=1)
    else:
        cleaned_body = cleaned
    marker = "# 清洗后转录"
    if marker in cleaned_body:
        cleaned_body = cleaned_body.split(marker, 1)[-1]
    haystack = nw(qa)
    sents = iter_sentences(cleaned_body)
    if not sents:
        return False, "no sentences in cleaned transcript"
    missing = [s for s in sents if nw(s) not in haystack]
    ratio = 1 - len(missing) / len(sents)
    quotes = quote_text(qa)
    char_ratio = len(nw(quotes)) / max(len(nw(cleaned_body)), 1)
    extra = ""
    if char_ratio > 1.0:
        extra = f"; char_ratio={char_ratio:.1%} >100% (duplicate signal)"
    if ratio < 0.90:
        sample = " | ".join(nw(s)[:24] for s in missing[:3])
        return False, f"coverage {ratio:.1%} < 90% ({len(missing)}/{len(sents)} missing){extra}; e.g. {sample}"
    return True, f"coverage {ratio:.1%} ({len(sents) - len(missing)}/{len(sents)}); quote/clean {char_ratio:.1%}{extra}"


def check_duplicates(qa_path: Path) -> tuple[bool, str]:
    text = qa_path.read_text(encoding="utf-8")
    quotes = quote_text(text)
    paras = [p.strip() for p in re.split(r"\n\s*\n", quotes) if len(nw(p)) > 40]
    counts = Counter(nw(p) for p in paras)
    dup_chars = sum((n - 1) * len(key) for key, n in counts.items() if n > 1)
    total = max(len(nw(quotes)), 1)
    rate = dup_chars / total
    identical: list[str] = []
    for block in re.split(r"(?=### Q\d+)", text):
        heading = re.search(r"### (Q\d+)", block)
        if not heading:
            continue
        question = re.search(r"- \*\*问题原文\*\*：\n(.*?)(?:\n- \*\*)", block, re.S)
        answer = re.search(r"- \*\*回答原文\*\*：\n(.*?)(?:\n- \*\*)", block, re.S)
        if not question or not answer:
            continue
        qn, an = nw(question.group(1)), nw(answer.group(1))
        if qn and qn == an and len(qn) > 40:
            identical.append(heading.group(1))
    if identical:
        return False, f"identical Q/A in {', '.join(identical)}; dup_rate={rate:.1%}"
    if rate > 0.05:
        return False, f"duplicate quote rate {rate:.1%} > 5%"
    return True, f"dup_rate={rate:.1%}; no identical Q/A"


def check_placeholders(files: list[Path]) -> tuple[bool, str]:
    hits: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        if PLACEHOLDER_RE.search(text):
            hits.append(path.name)
    if hits:
        return False, "placeholders in " + ", ".join(hits)
    return True, "no 〔 / TODO / 待补"


def check_links(files: list[Path], map_file: Path | None) -> tuple[bool, str]:
    if map_file is None:
        return False, "no document map"
    stems = {p.stem for p in files}
    text = map_file.read_text(encoding="utf-8")
    links = [m.group(1).strip() for m in WIKILINK_RE.finditer(text)]
    missing: list[str] = []
    checked = 0
    for link in links:
        is_packish = bool(NUMBERED_NAME_RE.match(link)) or "文档地图" in link
        if not is_packish:
            continue
        checked += 1
        if link not in stems:
            missing.append(link)
    if missing:
        return False, "unresolved pack links: " + ", ".join(missing)
    return True, f"{checked} pack wikilinks resolve"


def check_yaml(files: list[Path]) -> tuple[bool, str]:
    problems: list[str] = []
    for path in files:
        meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        required = REQUIRED_NUMBERED if NUMBERED_NAME_RE.match(path.name) else REQUIRED_ALL
        absent = [key for key in required if not meta.get(key)]
        if absent:
            problems.append(f"{path.name} missing {', '.join(absent)}")
    if problems:
        return False, "; ".join(problems)
    return True, f"{len(files)} files have required YAML"


CHECKS = [
    ("numbering", lambda ctx: check_numbering(ctx["files"])),
    ("01_role", lambda ctx: check_01_role(ctx["qa"])),
    ("coverage", lambda ctx: check_coverage(ctx["qa"], ctx["cleaned"])),
    ("duplicates", lambda ctx: check_duplicates(ctx["qa"])),
    ("placeholders", lambda ctx: check_placeholders(ctx["files"])),
    ("wikilinks", lambda ctx: check_links(ctx["files"], ctx["map"])),
    ("yaml", lambda ctx: check_yaml(ctx["files"])),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack-dir", required=True)
    parser.add_argument("--cleaned", required=True)
    args = parser.parse_args()

    pack_dir = Path(args.pack_dir).expanduser().resolve()
    cleaned = Path(args.cleaned).expanduser().resolve()
    if not pack_dir.is_dir():
        print(f"FAIL pack-dir not found: {pack_dir}", file=sys.stderr)
        return 2
    if not cleaned.is_file():
        print(f"FAIL cleaned transcript not found: {cleaned}", file=sys.stderr)
        return 2

    files = pack_files(pack_dir)
    ctx = {
        "files": files,
        "qa": find_01(files),
        "map": find_map(files),
        "cleaned": cleaned,
    }

    failed = 0
    print(f"pack: {pack_dir}")
    print(f"cleaned: {cleaned}")
    for name, fn in CHECKS:
        ok, detail = fn(ctx)
        status = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"{status}  {name}: {detail}")
    print(f"{'PASS' if failed == 0 else 'FAIL'}  {7 - failed}/7 checks")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
