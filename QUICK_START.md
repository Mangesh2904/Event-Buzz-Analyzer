# 🔥 Event Buzz Analyzer - Quick Start Guide

## What's New?

Instead of creating events with complex forms, you now **just enter an event name** and the system automatically analyzes its buzz across multiple platforms!

## How to Use

### Step 1: Start the Application
```bash
python app.py
```
Visit: `http://127.0.0.1:5000`

### Step 2: Search for an Event
- Go to the home page
- Click **"Search Event"** button
- Enter any event name:
  - ✅ "Bitcoin Surge" (recent/ongoing)
  - ✅ "World Cup 2022" (past)
  - ✅ "Paris Olympics 2024" (upcoming)
- System auto-generates date range (7 days before to 7 days after today)

### Step 3: Click "Analyze Event"
- System creates event entry in database
- Displays empty analysis dashboard

### Step 4: Click "Start Analysis"
- Data collection begins in background
- Fetches from Reddit, YouTube, and News APIs
- May take 1-2 minutes

### Step 5: View Results
Once data arrives, you'll see:

#### **Buzz Score (0-100)** 🎯
- 75+: 🔥 VIRAL - Massive engagement
- 50-74: 👍 GOOD - Solid engagement  
- 1-49: 📊 MODERATE - Room for growth
- 0: 😴 LOW - Low engagement

#### **Key Metrics** 📊
- Total mentions across all platforms
- Mentions before/during/after event
- Positive/Neutral/Negative split

#### **Sentiment Polarity** ❤️
- Shows sentiment trend over three periods
- Color coded: Red (negative) → Yellow (neutral) → Green (positive)

#### **AI Recommendations** 💡
- Actionable strategies based on metrics
- Platform recommendations
- Engagement boosting tips
- Sentiment response tactics

## Understanding the Charts

### Volume Chart 📈
- **X-axis**: Time (hourly bins)
- **Y-axis**: Number of mentions
- **Line**: Buzz trend over time

### Sentiment Chart 📉
- **Green Line**: Positive mentions trending up
- **Yellow Line**: Neutral mentions
- **Red Line**: Negative mentions (watch for spikes!)

## Data Sources

| Platform | What We Track |
|----------|---------------|
| **Reddit** | Subreddit posts, comments, upvotes |
| **YouTube** | Video titles, descriptions, upload timing |
| **News APIs** | Article mentions, news volume over time |

## Example Analysis

### Event: "Tesla Q3 Earnings"

**Pre-Event (Week Before)**
- 500 mentions total
- 60% positive, 30% neutral, 10% negative
- Polarity: +0.25 (slightly positive)

**During Event (Release Day)**
- 2,500 mentions (5x spike!)
- 45% positive, 35% neutral, 20% negative
- Polarity: +0.05 (neutral overall)

**Post-Event (Week After)**
- 800 mentions (declining)
- 55% positive, 30% neutral, 15% negative
- Polarity: +0.15

**Buzz Score: 68/100** 👍

**Recommendations:**
1. ✅ Event created strong spike in engagement
2. ⚠️ But sentiment dipped during release (negative news?)
3. 💡 Opportunity: Post positive follow-up content immediately after
4. 📱 Reddit had highest engagement - focus there for future events

## Troubleshooting

### Error: "Canvas is already in use"
✅ **FIXED** - Charts properly destroy old instances now

### Error: "date adapter not implemented"
✅ **FIXED** - Using formatted strings instead of date objects

### No data appearing?
1. Wait 1-2 minutes after clicking "Start Analysis"
2. Refresh page (F5)
3. Check if APIs are configured in `.env`:
   - `YOUTUBE_API_KEY`
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`

### Event not found?
- Name might be too specific or have typos
- Try broader event names
- App auto-creates if not found in DB

## Exporting Results

### Download as CSV
- Click "Export CSV"
- Get spreadsheet with all mentions
- Columns: platform, text, date, sentiment, polarity

### Download as PDF
- Click "Export PDF"
- Professional summary report
- Includes charts and recommendations

## Tips for Better Analysis

1. **Use specific event names**: "Apple iPhone 16 Launch" > "Apple Event"
2. **Popular events work better**: More mentions = better analysis
3. **Wait for data collection**: Don't refresh immediately
4. **Check back later**: More data arrives as platforms index content
5. **Compare events**: Search related events to compare buzz

## API Integration Examples

### Get Metrics Programmatically
```bash
curl http://127.0.0.1:5000/api/metrics/{event_id}
```

Response:
```json
{
  "timeseries": {
    "times": ["2025-10-22T12:00", ...],
    "counts": [10, 25, 45, ...],
    "positive": [8, 20, 35, ...],
    "negative": [1, 2, 5, ...],
    "neutral": [1, 3, 5, ...]
  },
  "summary": {
    "total": 1250,
    "buzz_score": 68,
    "during_polarity": 0.15,
    "platform_breakdown": {
      "reddit": 600,
      "youtube": 400,
      "news": 250
    }
  }
}
```

## Feature Comparison: Old vs New

| Feature | Old | New |
|---------|-----|-----|
| Event Creation | Complex form (dates, hashtags, keywords) | Simple event name input |
| Date Range | Manual selection required | Auto-generated (7 days) |
| Dashboard | Required manual refresh | Auto-refreshes every 30s |
| Recommendations | Basic text | AI-generated with icons |
| Buzz Metric | None | Dynamic score (0-100) |
| Polarity Display | Raw number | Color-coded progress bars |
| Error Handling | Chart crashes | Graceful degradation |

## Contact & Support

For issues or feature requests:
1. Check the CHANGES.md file for detailed technical info
2. Review browser console (F12) for JavaScript errors
3. Check MongoDB connection in config.py

---

**Happy Analyzing!** 🚀
Last Updated: October 22, 2025
