# Daily Tech Digest

YouTube 구독 채널의 신규 영상을 매일 자동으로 수집하고, NotebookLM을 통해 브리핑 리포트와 슬라이드를 생성하는 파이프라인.

## 동작 흐름

```
fetch_youtube.py → videos.json → create_digest.py → NotebookLM (리포트 + 슬라이드)
```

1. **fetch_youtube.py** — YouTube Data API로 구독 채널의 최근 24시간 영상을 수집하여 `videos.json`으로 저장
2. **create_digest.py** — 수집된 영상 URL을 NotebookLM 노트북에 소스로 추가하고, 한국어 브리핑 리포트와 슬라이드 덱을 생성 요청
3. **run.sh** — 위 두 스크립트를 순서대로 실행하는 cron용 래퍼 (로깅, 에러 처리 포함)

## 사전 준비

### YouTube API

1. [Google Cloud Console](https://console.cloud.google.com/)에서 YouTube Data API v3 활성화
2. OAuth 2.0 클라이언트 ID 생성 → `daily-tech-digest-client.json`으로 저장
3. 최초 1회 수동 실행하여 `token.json` 생성:
   ```bash
   uv run python fetch_youtube.py
   ```

### NotebookLM

1. `notebooklm-mcp-cli` 설치:
   ```bash
   uv tool install notebooklm-mcp-cli
   ```
2. 인증:
   ```bash
   nlm login
   ```
   Chrome에 Google 계정 로그인이 되어 있어야 합니다.

## 수동 실행

```bash
# 개별 실행
uv run python fetch_youtube.py
uv run python create_digest.py

# 전체 파이프라인
./run.sh
```

## cron 자동 실행

```bash
crontab -e
```

```
0 6 * * * /path/to/daily-tech-digest/run.sh
```

실행 로그는 `logs/YYYY-MM-DD.log`에 기록됩니다.

## 프로젝트 구조

```
daily-tech-digest/
├── fetch_youtube.py              # YouTube 구독 영상 수집
├── create_digest.py              # NotebookLM 리포트/슬라이드 생성
├── run.sh                        # cron 자동 실행 스크립트
├── daily-tech-digest-client.json # YouTube OAuth 클라이언트 (비공개)
├── token.json                    # YouTube OAuth 토큰 (비공개)
├── videos.json                   # 수집된 영상 목록 (매일 덮어쓰기)
├── pyproject.toml
└── logs/                         # 실행 로그 (.gitignore)
```

## 알려진 제한사항

- **YouTube OAuth refresh_token 만료**: 토큰이 revoke되면 브라우저 인증이 필요하므로 cron에서 실패합니다. `token.json`을 삭제하고 수동으로 `fetch_youtube.py`를 재실행하세요.
- **NotebookLM 쿠키 만료**: `run.sh`가 매 실행마다 `nlm login`을 수행하지만, Chrome에 Google 로그인이 풀려 있으면 실패합니다.
- **영상 0개인 날**: `videos.json`이 생성되지 않으므로 `create_digest.py`는 자동으로 스킵됩니다.
