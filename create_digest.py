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

SLIDE_FOCUS_PROMPT_TEMPLATE = """\
추가된 소스들은 오늘 내가 구독한 YouTube 채널에서 업로드된 영상들입니다.
이 영상들을 분석하여 오늘의 YouTube 구독 피드 슬라이드를 만들어 주세요.

슬라이드 구성:
1번 슬라이드: 날짜 "{date}", 전체 영상 수, 채널 목록을 담은 커버 슬라이드
각 영상별 슬라이드: 영상 1개당 최소 2~3장의 슬라이드를 사용하세요.
  - 1장: 채널명, 영상 제목, 핵심 주제 개요
  - 2장: 영상에서 다루는 개념, 흐름, 주장을 문단 수준으로 상세히 설명. \
짧은 bullet point가 아니라 충분한 맥락이 담긴 설명을 작성해 주세요.
  - 3장(선택): 기술 용어 해설, 딥다이브 인사이트, 또는 관련 배경 지식
마지막 슬라이드: 오늘 전체 영상들의 공통 주제나 트렌드 총정리"""

REPORT_CUSTOM_PROMPT_TEMPLATE = """\
당신은 테크 전문 에디터입니다. 소스로 추가된 YouTube 영상들을 바탕으로 \
{date}의 기술 뉴스 브리핑 문서를 작성하세요.

반드시 지켜야 할 규칙:
- 영상 하나당 최소 500단어 이상 할애하세요. 짧게 요약하지 마세요.
- 모든 영상을 빠짐없이 다루세요.

문서 형식:

# 오늘의 개요
날짜, 총 영상 수, 다룬 채널 목록을 표로 정리.

# 영상별 상세 분석
영상마다 아래 구조로 작성:

## [채널명] 영상 제목
### 내용 정리
영상이 다루는 주제의 배경부터 시작하세요. 왜 이 주제가 지금 화제인지, \
어떤 맥락에서 나온 이야기인지 설명한 뒤, 영상에서 전달하는 핵심 정보와 \
주장을 순서대로 풀어 쓰세요. 영상의 논리 흐름을 따라가며 구체적인 사례, \
수치, 비교 등 중요한 디테일을 포함하세요.

### 기술 용어 해설
영상에 등장하는 전문 용어를 bullet point로 정리하고 각각 1~2문장으로 설명.

### 왜 주목해야 하나
이 주제가 업계에 미치는 영향, 앞으로의 전망, 개발자/사용자 관점에서의 의미.

# 오늘의 트렌드 총정리
모든 영상을 관통하는 공통 주제, 기술 흐름, 주목할 시사점을 정리."""

def build_slide_prompt(date: str) -> str:
    return SLIDE_FOCUS_PROMPT_TEMPLATE.format(date=date)

def build_report_prompt(date: str) -> str:
    return REPORT_CUSTOM_PROMPT_TEMPLATE.format(date=date)


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

            # 3. 리포트(Briefing Doc) 생성 요청
            print("[3/4] 리포트 생성 요청 중...")
            report_result = client.create_report(
                notebook_id=notebook_id,
                report_format="Create Your Own",
                custom_prompt=build_report_prompt(today),
                language="ko",
            )
            print(f"  요청 완료 (artifact_id: {report_result.get('artifact_id')})")

            # 4. 슬라이드 생성 요청
            print("[4/4] 슬라이드 생성 요청 중...")
            slide_result = client.create_slide_deck(
                notebook_id=notebook_id,
                focus_prompt=build_slide_prompt(today),
                language="ko",
            )
            print(f"  요청 완료 (artifact_id: {slide_result.get('artifact_id')})")
            print(f"\n완료! NotebookLM에서 리포트와 슬라이드가 생성됩니다.")
            print(f"확인: https://notebooklm.google.com/notebook/{notebook_id}")

    except ClientAuthenticationError:
        print("인증 만료. 'nlm login'을 다시 실행해 주세요.")
        sys.exit(1)
    except NotebookLMError as e:
        print(f"NotebookLM 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
