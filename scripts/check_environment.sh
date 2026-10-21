#!/usr/bin/env bash
set -euo pipefail
printf '\nDESTINY Phase 1 environment check\n'
printf 'Working directory: '; pwd
printf 'Python: '; python3 --version || true
printf 'Node: '; node --version || true
printf 'npm: '; npm --version || true
printf 'git: '; git --version || true
printf '\nRepository:\n'
git status --short 2>/dev/null || true
printf '\nConfigured remotes:\n'
git remote -v 2>/dev/null || true
printf '\nGPU (optional):\n'
command -v nvidia-smi >/dev/null && nvidia-smi -L || true
printf '\nNever submit HUNT data or personal secrets to this script.\n'
