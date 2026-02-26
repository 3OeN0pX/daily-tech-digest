"""YouTube 구독 피드 → NotebookLM 리포트/슬라이드 자동 생성.

영상 1개당 노트북 1개를 생성하여 리포트와 슬라이드를 각각 만든다.

사용법:
  1. uv run python fetch_youtube.py  → videos.json 생성
  2. uv run python create_digest.py  → NotebookLM 노트북 생성
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

from notebooklm_tools.core.auth import load_cached_tokens
from notebooklm_tools.core.client import NotebookLMClient
from notebooklm_tools.core.errors import ClientAuthenticationError, NotebookLMError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KST = timezone(timedelta(hours=9))

REPORT_PROMPT = (
    "Create a comprehensive briefing document that synthesizes the main themes "
    "and ideas from the sources. Start with a concise Executive Summary that "
    "presents the most critical takeaways upfront. The body of the document must "
    "provide a detailed and thorough examination of the main themes, evidence, "
    "and conclusions found in the sources. This analysis should be structured "
    "logically with headings and bullet points to ensure clarity. The tone must "
    "be objective and incisive."
)


def load_videos():
    path = os.path.join(BASE_DIR, "videos.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def process_video(client, today, index, total, video):
    """영상 1개에 대해 노트북 생성 → 소스 추가 → 리포트 생성."""
    title = f"{today} - {video['title']}"
    prefix = f"  [{index}/{total}]"

    # 1. 노트북 생성
    print(f"{prefix} 노트북 생성: {video['title'][:50]}...")
    notebook = client.create_notebook(title)
    notebook_id = notebook.id

    # 2. 소스 추가
    print(f"{prefix} 소스 추가 중...")
    client.add_url_source(
        notebook_id=notebook_id,
        url=video["url"],
        wait=True,
        wait_timeout=120.0,
    )

    # 3. 리포트 생성
    print(f"{prefix} 리포트 생성 요청...")
    client.create_report(
        notebook_id=notebook_id,
        report_format="Create Your Own",
        custom_prompt=REPORT_PROMPT,
        language="ko",
    )

    print(f"{prefix} 완료 → https://notebooklm.google.com/notebook/{notebook_id}")


def main():
    tokens = load_cached_tokens()
    if not tokens:
        print("인증 정보가 없습니다. 먼저 'nlm login'을 실행해 주세요.")
        sys.exit(1)

    videos = load_videos()
    today = datetime.now(KST).strftime("%Y-%m-%d")

    print(f"날짜: {today}")
    print(f"영상 수: {len(videos)}개\n")

    try:
        with NotebookLMClient(
            cookies=tokens.cookies,
            csrf_token=tokens.csrf_token,
            session_id=tokens.session_id,
        ) as client:
            for i, video in enumerate(videos, 1):
                try:
                    process_video(client, today, i, len(videos), video)
                except NotebookLMError as e:
                    print(f"  [{i}/{len(videos)}] ERROR: {video['title'][:50]} - {e}")
                    continue

    except ClientAuthenticationError:
        print("인증 만료. 'nlm login'을 다시 실행해 주세요.")
        sys.exit(1)

    print(f"\n=== 전체 완료 ({len(videos)}개 영상) ===")


if __name__ == "__main__":
    main()
