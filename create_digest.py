"""YouTube 구독 피드 → NotebookLM 슬라이드 자동 생성.

사용법:
  1. uv run python fetch_youtube.py  → videos.json 생성
  2. uv run python create_digest.py  → NotebookLM 슬라이드 PDF 생성
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

FOCUS_PROMPT = """\
추가된 소스들은 오늘 내가 구독한 YouTube 채널에서 업로드된 영상들입니다.
이 영상들을 분석하여 오늘의 YouTube 구독 피드 슬라이드를 만들어 주세요.

슬라이드 구성:
1번 슬라이드: 오늘 날짜, 전체 영상 수, 채널 목록을 담은 커버 슬라이드
각 영상별 슬라이드: 채널명, 영상 제목, 영상의 주요 내용을 최대한 상세하게 담아주세요. \
단순 요약보다는 영상에서 다루는 개념, 흐름, 주장을 충실히 전달해 주세요.
기술 용어 설명: 영상에서 등장하는 전문적이거나 난이도 있는 용어와 개념은 별도로 설명을 추가해 주세요.
딥다이브 인사이트: 각 영상에서 단순히 전달된 내용을 넘어, 이 기술이나 주제가 갖는 의미, \
앞으로의 방향성, 주목해야 할 이유 등 심층적인 관점을 추가해 주세요.
마지막 슬라이드: 오늘 전체 영상들의 공통 주제나 트렌드 총정리"""


def load_videos():
    path = os.path.join(BASE_DIR, "videos.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    # 인증 확인
    tokens = load_cached_tokens()
    if not tokens:
        print("인증 정보가 없습니다. 먼저 'nlm login'을 실행해 주세요.")
        sys.exit(1)

    videos = load_videos()
    today = datetime.now(KST).strftime("%Y-%m-%d")
    title = f"{today} Tech Digest"
    output_file = os.path.join(BASE_DIR, f"{today}-digest.pdf")

    print(f"날짜: {today}")
    print(f"영상 수: {len(videos)}개")
    print(f"노트북 제목: {title}\n")

    try:
        with NotebookLMClient(
            cookies=tokens.cookies,
            csrf_token=tokens.csrf_token,
            session_id=tokens.session_id,
        ) as client:
            # 1. 노트북 생성
            print("[1/3] 노트북 생성 중...")
            notebook = client.create_notebook(title)
            notebook_id = notebook.id
            print(f"  생성 완료: {notebook_id}")

            # 2. 소스 추가
            print(f"[2/3] 소스 추가 중 ({len(videos)}개)...")
            for i, v in enumerate(videos, 1):
                print(f"  ({i}/{len(videos)}) {v['title'][:50]}...")
                client.add_url_source(
                    notebook_id=notebook_id,
                    url=v["url"],
                    wait=True,
                    wait_timeout=120.0,
                )
            print("  소스 추가 완료")

            # 3. 슬라이드 생성 요청
            print("[3/3] 슬라이드 생성 요청 중...")
            result = client.create_slide_deck(
                notebook_id=notebook_id,
                focus_prompt=FOCUS_PROMPT,
            )
            print(f"  요청 완료 (artifact_id: {result.get('artifact_id')})")
            print(f"\n완료! NotebookLM에서 슬라이드가 생성됩니다.")
            print(f"확인: https://notebooklm.google.com/notebook/{notebook_id}")

    except ClientAuthenticationError:
        print("인증 만료. 'nlm login'을 다시 실행해 주세요.")
        sys.exit(1)
    except NotebookLMError as e:
        print(f"NotebookLM 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
