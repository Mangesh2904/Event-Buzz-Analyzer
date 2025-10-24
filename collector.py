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
        print("⚠️  Reddit credentials not set, skipping Reddit fetch")
        return 0
    
    count = 0
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
            count += 1
        
        print(f"   → Reddit: {count} posts collected")
        return count
        
    except Exception as e:
        print(f"❌ Reddit fetch error: {e}")
        return 0

def youtube_fetch(event_id, query, published_after, published_before, max_results=50):
    if not Config.YOUTUBE_API_KEY:
        print("⚠️  YouTube API key not set, skipping YouTube fetch")
        return 0
    
    count = 0
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
            count += 1
        
        print(f"   → YouTube: {count} videos collected")
        return count
        
    except Exception as e:
        print(f"❌ YouTube fetch error: {e}")
        return 0

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
    
    count = 0
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # The GDELT timeline volumes (counts per day) are returned; we'll convert each day to a document
        for rec in data.get("timeline", []):
            # rec example: {"date":"20251022","value": 234}
            date_str = rec["date"]
            count_val = rec["value"]
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
                "metrics": {"news_count": count_val},
                "source": "gdelt_summary"
            })
            count += 1
        
        print(f"   → News: {count} data points collected")
        return count
    except Exception as e:
        print(f"❌ News fetch error: {e}")
        return 0

def start_collection_thread(event_id):
    def runner():
        try:
            ev = get_event(event_id)
            if not ev:
                print(f"❌ Event not found: {event_id}")
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
            query = " OR ".join(query_terms) if query_terms else ev.get("name", "")

            print(f"🚀 Starting collection for event: {ev.get('name')}")
            print(f"   Event ID: {event_id}")
            print(f"   Query: '{query}'")
            print(f"   Time range: {pre_start} to {post_end}")

            reddit_count = 0
            youtube_count = 0
            news_count = 0

            # Reddit
            try:
                before_reddit = Config.MONGO_URI and True  # Check if we can count
                reddit_fetch(event_id, query, pre_start, post_end, limit=200)
                # Count how many were added (approximate)
                print(f"✓ Reddit fetch completed")
            except Exception as e:
                print(f"✗ Reddit fetch failed: {e}")

            # YouTube
            try:
                youtube_fetch(event_id, query, pre_start, post_end, max_results=30)
                print(f"✓ YouTube fetch completed")
            except Exception as e:
                print(f"✗ YouTube fetch failed: {e}")

            # News
            try:
                news_fetch(event_id, query, pre_start.date(), post_end.date())
                print(f"✓ News fetch completed")
            except Exception as e:
                print(f"✗ News fetch failed: {e}")

            print(f"✅ Collection complete for event: {ev.get('name')} (ID: {event_id})")
            
        except Exception as e:
            print(f"❌ Collection thread failed: {e}")
            traceback.print_exc()

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    return t
