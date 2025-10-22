from pymongo import MongoClient
from config import Config
from datetime import datetime, timedelta
from bson.objectid import ObjectId

# Lazy connection - don't connect on import
_client = None
_db = None

def _get_connection():
    """Lazy connection to MongoDB"""
    global _client, _db
    if _client is None:
        _client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
        _db = _client.get_default_database()
    return _db

def _get_events_coll():
    return _get_connection().events

def _get_tweets_coll():
    return _get_connection().tweets

def create_event(event_data):
    event_data = event_data.copy()
    event_data['created_at'] = datetime.utcnow()
    result = _get_events_coll().insert_one(event_data)
    return str(result.inserted_id)

def get_event(event_id):
    try:
        doc = _get_events_coll().find_one({"_id": ObjectId(event_id)})
    except:
        # Invalid ObjectId format
        return None
    if doc:
        doc['_id'] = str(doc['_id'])
    return doc

def find_event_by_name(event_name):
    """Find event by name (case-insensitive)"""
    doc = _get_events_coll().find_one({"name": {"$regex": f"^{event_name}$", "$options": "i"}})
    if doc:
        doc['_id'] = str(doc['_id'])
    return doc

def search_or_create_event(event_name):
    """Search for event by name, or create if not exists"""
    existing = find_event_by_name(event_name)
    if existing:
        return existing['_id']
    
    # Create new event with auto-generated date range
    now = datetime.utcnow()
    start_time = now - timedelta(days=7)
    end_time = now + timedelta(days=7)
    
    event_data = {
        "name": event_name,
        "description": f"Auto-analyzed event: {event_name}",
        "hashtags": [event_name.replace(" ", "")],
        "keywords": event_name,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "auto_created": True,
        "created_at": datetime.utcnow()
    }
    
    result = _get_events_coll().insert_one(event_data)
    return str(result.inserted_id)

def list_events():
    out = []
    for d in _get_events_coll().find().sort("created_at", -1):
        d['_id'] = str(d['_id'])
        out.append(d)
    return out

def save_tweet(tweet_doc):
    tweet_doc['cached_at'] = datetime.utcnow()
    return _get_tweets_coll().insert_one(tweet_doc)

def get_tweets_for_event(event_id, start=None, end=None):
    q = {"event_id": event_id}
    if start or end:
        q['created_at'] = {}
        if start: q['created_at']['$gte'] = start
        if end: q['created_at']['$lte'] = end
    return list(_get_tweets_coll().find(q).sort("created_at", 1))

def count_tweets_filter(event_id, start=None, end=None, sentiment=None):
    q = {"event_id": event_id}
    if sentiment:
        q['sentiment'] = sentiment
    if start or end:
        q['created_at'] = {}
        if start: q['created_at']['$gte'] = start
        if end: q['created_at']['$lte'] = end
    return _get_tweets_coll().count_documents(q)
