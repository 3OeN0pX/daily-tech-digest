"""매일 YouTube 구독 채널의 신규 영상을 수집하는 스크립트.

전일 05:00 KST ~ 금일 05:00 KST 사이에 업로드된 영상을 출력한다.
"""

import json
import os
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET = os.path.join(BASE_DIR, "daily-tech-digest-client.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

KST = timezone(timedelta(hours=9))


def authenticate():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def get_subscriptions(youtube):
    """구독 채널 ID 목록을 반환한다."""
    channel_ids = []
    request = youtube.subscriptions().list(
        part="snippet", mine=True, maxResults=50
    )
    while request:
        response = request.execute()
        for item in response["items"]:
            channel_ids.append(item["snippet"]["resourceId"]["channelId"])
        request = youtube.subscriptions().list_next(request, response)
    return channel_ids


def get_uploads_playlist_id(youtube, channel_id):
    """채널의 uploads playlist ID를 반환한다."""
    response = youtube.channels().list(
        part="contentDetails", id=channel_id
    ).execute()
    if response["items"]:
        return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    return None


def get_recent_videos(youtube, playlist_id, after, before):
    """playlist에서 기간 내 업로드된 영상 목록을 반환한다."""
    videos = []
    request = youtube.playlistItems().list(
        part="snippet", playlistId=playlist_id, maxResults=50
    )
    while request:
        response = request.execute()
        for item in response["items"]:
            published = datetime.fromisoformat(
                item["snippet"]["publishedAt"].replace("Z", "+00:00")
            )
            if published < after:
                # 최신순이므로 범위 이전이면 중단
                return videos
            if published < before:
                videos.append({
                    "title": item["snippet"]["title"],
                    "video_id": item["snippet"]["resourceId"]["videoId"],
                    "channel": item["snippet"]["channelTitle"],
                    "published": published,
                })
        request = youtube.playlistItems().list_next(request, response)
    return videos


def main():
    now_kst = datetime.now(KST)
    today_5am = now_kst.replace(hour=5, minute=0, second=0, microsecond=0)
    if now_kst < today_5am:
        today_5am -= timedelta(days=1)
    yesterday_5am = today_5am - timedelta(days=1)

    creds = authenticate()
    youtube = build("youtube", "v3", credentials=creds)

    channel_ids = get_subscriptions(youtube)
    print(f"구독 채널 수: {len(channel_ids)}")

    all_videos = []
    for ch_id in channel_ids:
        playlist_id = get_uploads_playlist_id(youtube, ch_id)
        if not playlist_id:
            continue
        videos = get_recent_videos(youtube, playlist_id, yesterday_5am, today_5am)
        all_videos.extend(videos)

    all_videos.sort(key=lambda v: v["published"], reverse=True)

    if not all_videos:
        print("오늘 업로드된 영상이 없습니다.")
        return

    print(f"\n총 {len(all_videos)}개 영상 발견:\n")
    for v in all_videos:
        print(f"[{v['channel']}] {v['title']}")
        print(f"  https://www.youtube.com/watch?v={v['video_id']}")
        print()

    # videos.json 저장
    videos_json = [
        {
            "title": v["title"],
            "url": f"https://www.youtube.com/watch?v={v['video_id']}",
            "channel": v["channel"],
        }
        for v in all_videos
    ]
    output_path = os.path.join(BASE_DIR, "videos.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(videos_json, f, ensure_ascii=False, indent=2)
    print(f"videos.json 저장 완료 ({len(videos_json)}개 영상)")


if __name__ == "__main__":
    main()
