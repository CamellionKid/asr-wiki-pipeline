#!/usr/bin/env bash
# Install the ASR Wiki Pipeline skills into local agent skill directories.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$ROOT/skills"

SKILLS=(
  asr-pipeline
  asr-cleaner
  talk-share-extract
  interview-qa-extract
  interview-self-analysis
  interview-observer-analysis
  interview-round-compare
  experience-extraction
)

TARGETS=(
  "$HOME/.agents/skills"
  "$HOME/.claude/skills"
  "$HOME/.cursor/skills"
  "$HOME/.codex/skills"
  "$HOME/.gemini/config/skills"
  "$HOME/.gemini/skills"
  "$HOME/.config/opencode/skills"
)

if [[ ! -d "$SKILLS_DIR/asr-pipeline" ]]; then
  echo "error: $SKILLS_DIR/asr-pipeline not found" >&2
  exit 1
fi

linked=0
skipped=0
for target in "${TARGETS[@]}"; do
  if [[ ! -d "$target" ]]; then
    echo "skip  $target (directory missing)"
    skipped=$((skipped + 1))
    continue
  fi
  for skill in "${SKILLS[@]}"; do
    ln -sfn "$SKILLS_DIR/$skill" "$target/$skill"
    echo "link  $target/$skill"
    linked=$((linked + 1))
  done
done

echo
echo "done: $linked symlink(s) created, $skipped target dir(s) skipped."
echo "entry skill: asr-pipeline"
echo "verify a pack after writing:"
echo "  python3 \"$SKILLS_DIR/asr-pipeline/scripts/verify_pack.py\" --pack-dir <pack> --cleaned <cleaned-transcript.md>"
