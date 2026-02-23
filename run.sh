#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
DATE=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/$DATE.log"

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:$PATH"

mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

log "=== Daily Tech Digest 시작 ==="

# Step 0: notebooklm-mcp-cli 업그레이드 + 인증 갱신
log "Step 0: nlm 업그레이드 및 인증 갱신"
uv tool upgrade notebooklm-mcp-cli >> "$LOG_FILE" 2>&1 || true
if ! nlm login >> "$LOG_FILE" 2>&1; then
    log "WARNING: nlm login 실패 (Chrome Google 로그인 확인 필요)"
fi

# Step 1: YouTube 영상 수집
log "Step 1: fetch_youtube.py"
if ! uv run --directory "$SCRIPT_DIR" python fetch_youtube.py >> "$LOG_FILE" 2>&1; then
    log "ERROR: fetch_youtube.py 실패 (YouTube 토큰 확인 필요)"
    exit 1
fi

# Step 2: 영상 존재 확인
if [ ! -f "$SCRIPT_DIR/videos.json" ]; then
    log "오늘 영상 없음. 종료."
    exit 0
fi

# Step 3: NotebookLM 슬라이드 생성 요청
log "Step 2: create_digest.py"
if ! uv run --directory "$SCRIPT_DIR" python create_digest.py >> "$LOG_FILE" 2>&1; then
    log "ERROR: create_digest.py 실패 (nlm login 필요할 수 있음)"
    exit 1
fi

log "=== 완료 ==="
