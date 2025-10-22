import threading
import time
import traceback
from datetime import datetime, timedelta
import requests
from textblob import TextBlob

from config import Config
from models import save_tweet, get_event

import praw
from googleapiclient.discovery import build

### Helper functions
def analyze_sentiment(text):
    blob = TextBlob(text)
    polarity = round(blob.sentiment.polarity, 4)
    if polarity > 0.05:
        label = "positive"
    elif polarity < -0.05:
        label = "negative"
    else:
        label = "neutral"
    return {"polarity": polarity, "label": label}

def reddit_fetch(event_id, query, after, before, limit=200):
    if not Config.REDDIT_CLIENT_ID or not Config.REDDIT_CLIENT_SECRET:
        print("Reddit credentials not set, skipping Reddit fetch")
        return
    try:
        reddit = praw.Reddit(
            client_id=Config.REDDIT_CLIENT_ID,
            client_secret=Config.REDDIT_CLIENT_SECRET,
            user_agent=Config.REDDIT_USER_AGENT
        )
        subreddit = reddit.subreddit("all")
        for submission in subreddit.search(query, sort="new", time_filter="year", limit=limit):
            created = datetime.utcfromtimestamp(submission.created_utc)
            if created < after or created > before:
                continue
            text = (submission.title or "") + " " + (submission.selftext or "")
            sentiment = analyze_sentiment(text)
            save_tweet({
                "event_id": event_id,
                "platform": "reddit",
                "text": text,
                "created_at": created,
                "sentiment": sentiment['label'],
                "polarity": sentiment['polarity'],
                "metrics": {"score": submission.score, "num_comments": submission.num_comments},
                "source": "reddit_submission"
            })
    except Exception as e:
        print(f"Reddit fetch error: {e}")

def youtube_fetch(event_id, query, published_after, published_before, max_results=50):
    if not Config.YOUTUBE_API_KEY:
        print("YouTube API key not set, skipping YouTube fetch")
        return
    try:
        youtube = build("youtube", "v3", developerKey=Config.YOUTUBE_API_KEY)
        # search videos
        search_response = youtube.search().list(
            q=query,
            part="id,snippet",
            type="video",
            publishedAfter=published_after.isoformat("T") + "Z",
            publishedBefore=published_before.isoformat("T") + "Z",
            maxResults=max_results
        ).execute()
        for item in search_response.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            description = item["snippet"]["description"]
            published_at = datetime.fromisoformat(item["snippet"]["publishedAt"].rstrip("Z"))
            full_text = title + " " + description
            sentiment = analyze_sentiment(full_text)
            save_tweet({
                "event_id": event_id,
                "platform": "youtube",
                "text": full_text,
                "created_at": published_at,
                "sentiment": sentiment['label'],
                "polarity": sentiment['polarity'],
                "metrics": {"video_id": video_id},
                "source": "youtube_video"
            })
            # Optionally fetch comments (but skip to keep quota low)
        # Note: each search list costs quota units — keep max_results low.
    except Exception as e:
        print(f"YouTube fetch error: {e}")

def news_fetch(event_id, query, start_date, end_date):
    # Use GDELT summary endpoint (free) to get counts and approximate sentiment/tone
    # Example: https://api.gdeltproject.org/api/v2/summary/summary?d=web&t=compare&q1=query&d1=start_date&d2=end_date
    params = {
        "d": "web",
        "t": "timelinevol",
        "q": query,
        "d1": start_date.strftime("%Y%m%d"),
        "d2": end_date.strftime("%Y%m%d")
    }
    url = Config.GDELT_BASE_URL + "summary/summary"
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # The GDELT timeline volumes (counts per day) are returned; we'll convert each day to a document
        for rec in data.get("timeline", []):
            # rec example: {"date":"20251022","value": 234}
            date_str = rec["date"]
            count = rec["value"]
            created = datetime.strptime(date_str, "%Y%m%d")
            # we treat each day's count as one item
            sentiment_label = "neutral"
            polarity = 0.0
            # Save as synthetic “news count”
            save_tweet({
                "event_id": event_id,
                "platform": "news",
                "text": f"News volume for {query} on {date_str}",
                "created_at": created,
                "sentiment": sentiment_label,
                "polarity": polarity,
                "metrics": {"news_count": count},
                "source": "gdelt_summary"
            })
    except Exception as e:
        print("GDELT fetch error:", e)

def start_collection_thread(event_id):
    def runner():
        ev = get_event(event_id)
        if not ev:
            print("Event not found:", event_id)
            return
        from dateutil import parser
        start = parser.isoparse(ev.get("start_time"))
        end = parser.isoparse(ev.get("end_time"))
        pre_start = start - timedelta(hours=24)
        pre_end = start - timedelta(seconds=1)
        post_start = end + timedelta(seconds=1)
        post_end = end + timedelta(hours=24)

        # Build query
        hashtags = ev.get("hashtags", [])
        query_terms = hashtags.copy()
        if ev.get("keywords"):
            query_terms.extend([ev.get("keywords")])
        query = " OR ".join(query_terms)

        print(f"Collecting for event {event_id}: query='{query}'")

        # Reddit
        reddit_fetch(event_id, query, pre_start, post_end, limit=200)

        # YouTube
        youtube_fetch(event_id, query, pre_start, post_end, max_results=30)

        # News
        news_fetch(event_id, query, pre_start.date(), post_end.date())

        print("Collection complete for event", event_id)

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    return t
