from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
from config import Config
from models import (
    create_event, list_events, get_event, get_tweets_for_event, 
    search_or_create_event, find_event_by_name
)
from collector import start_collection_thread
from datetime import datetime, timedelta
import os, csv, io
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from bson.objectid import ObjectId

app = Flask(__name__)
app.config.from_object(Config)

if not os.path.exists(app.config['EXPORT_FOLDER']):
    os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    recent_events = list_events()
    return render_template("index.html", events=recent_events)

@app.route('/search', methods=['GET', 'POST'])
def search_event():
    """Search for an event by name and analyze buzz"""
    if request.method == 'POST':
        event_name = request.form.get('event_name', '').strip()
        if not event_name:
            flash("Please enter an event name.", "warning")
            return redirect(url_for('search_event'))
        
        # Try to find existing event or create a new one
        event_id = search_or_create_event(event_name)
        return redirect(url_for('analyze', event_id=event_id))
    
    return render_template("search_event.html")

@app.route('/analyze/<event_id>')
def analyze(event_id):
    """Analyze buzz and sentiment for an event"""
    ev = get_event(event_id)
    if not ev:
        flash("Event not found.", "danger")
        return redirect(url_for('index'))
    return render_template("analyze.html", event=ev)

@app.route('/events/new', methods=['GET','POST'])
def create_event_route():
    """Legacy endpoint - now redirects to search"""
    return redirect(url_for('search_event'))

@app.route('/dashboard/<event_id>')
def dashboard(event_id):
    """Legacy endpoint - now redirects to analyze"""
    return redirect(url_for('analyze', event_id=event_id))

def iso_to_dt(s):
    if s is None: return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        try:
            from dateutil import parser
            return parser.isoparse(s)
        except Exception:
            return None

@app.route('/api/metrics/<event_id>')
def api_metrics(event_id):
    """Get buzz metrics and sentiment analysis for an event"""
    ev = get_event(event_id)
    if not ev:
        return jsonify({"error":"event not found"}), 404

    # If start/end times not set, use current time as reference
    start = iso_to_dt(ev.get("start_time"))
    end = iso_to_dt(ev.get("end_time"))
    
    if not start:
        start = datetime.utcnow() - timedelta(days=7)
    if not end:
        end = datetime.utcnow() + timedelta(days=7)
    
    pre_start = start - timedelta(hours=24)
    post_end = end + timedelta(hours=24)

    tweets = get_tweets_for_event(event_id, start=pre_start, end=post_end)
    
    if not tweets:
        return jsonify({
            "timeseries": {"times":[], "counts":[], "positive":[], "neutral":[], "negative":[]},
            "summary": {"total": 0, "pre": 0, "during": 0, "post": 0, "pos": 0, "neg": 0, "neu": 0}
        })
    
    df = pd.DataFrame([{
        "created_at": t.get("created_at"),
        "sentiment": t.get("sentiment"),
        "polarity": t.get("polarity", 0),
        "platform": t.get("platform", "unknown"),
    } for t in tweets])

    df['created_at'] = pd.to_datetime(df['created_at'])
    df.set_index('created_at', inplace=True)

    counts = df.resample('1H').size().rename("count")
    counts = counts.reindex(pd.date_range(pre_start, post_end, freq='1H'), fill_value=0)

    pos = df[df.sentiment=="positive"].resample('1H').size().reindex(counts.index, fill_value=0)
    neg = df[df.sentiment=="negative"].resample('1H').size().reindex(counts.index, fill_value=0)
    neu = df[df.sentiment=="neutral"].resample('1H').size().reindex(counts.index, fill_value=0)

    times = [ts.isoformat() for ts in counts.index]

    total = len(df)
    pre_count = df.loc[pre_start:start - timedelta(seconds=1)].shape[0] if df.index.min() <= pre_start else 0
    during_count = df.loc[start:end].shape[0] if (df.index.min() <= end and df.index.max() >= start) else 0
    post_count = df.loc[end + timedelta(seconds=1):post_end].shape[0] if df.index.max() >= end else 0

    pos_total = pos.sum()
    neg_total = neg.sum()
    neu_total = neu.sum()

    def mean_pol(a, b):
        try:
            s = df.loc[a:b]['polarity']
            return float(s.mean()) if not s.empty else 0.0
        except:
            return 0.0

    pre_pol = mean_pol(pre_start, start - timedelta(seconds=1))
    during_pol = mean_pol(start, end)
    post_pol = mean_pol(end + timedelta(seconds=1), post_end)

    # Get platform breakdown
    platform_counts = df['platform'].value_counts().to_dict()

    summary = {
        "total": int(total),
        "pre": int(pre_count),
        "during": int(during_count),
        "post": int(post_count),
        "pos": int(pos_total),
        "neg": int(neg_total),
        "neu": int(neu_total),
        "pre_polarity": round(pre_pol, 4),
        "during_polarity": round(during_pol, 4),
        "post_polarity": round(post_pol, 4),
        "platform_breakdown": platform_counts,
        "buzz_score": calculate_buzz_score(total, during_pol, pre_count, during_count, post_count)
    }

    return jsonify({
        "timeseries": {
            "times": times,
            "counts": counts.tolist(),
            "positive": pos.tolist(),
            "negative": neg.tolist(),
            "neutral": neu.tolist()
        },
        "summary": summary
    })

def calculate_buzz_score(total, sentiment_polarity, pre_count, during_count, post_count):
    """Calculate a buzz score (0-100) based on various factors"""
    if total == 0:
        return 0
    
    # Volume factor (40%)
    max_volume = max(pre_count + during_count + post_count, 1)
    volume_score = min((total / max_volume) * 100, 100) * 0.4
    
    # Sentiment factor (30%)
    sentiment_score = ((sentiment_polarity + 1) / 2) * 100 * 0.3  # Convert from [-1, 1] to [0, 100]
    
    # Engagement factor (30%) - higher during event is better
    engagement_factor = (during_count / max(total, 1)) * 100 * 0.3
    
    buzz_score = volume_score + sentiment_score + engagement_factor
    return min(int(buzz_score), 100)

@app.route('/start_collection/<event_id>', methods=['POST'])
def start_collection(event_id):
    """Start collecting data for an event"""
    ev = get_event(event_id)
    if not ev:
        return jsonify({"error":"event not found"}), 404
    try:
        start_collection_thread(event_id)
        return jsonify({"status":"started"})
    except Exception as e:
        print(f"Error starting collection: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/export/csv/<event_id>')
def export_csv(event_id):
    """Export event data as CSV"""
    ev = get_event(event_id)
    if not ev:
        flash("Event not found", "danger")
        return redirect(url_for('index'))

    tweets = get_tweets_for_event(event_id)
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["platform","text","created_at","sentiment","polarity"])
    for t in tweets:
        cw.writerow([t.get('platform'), t.get('text'), t.get('created_at'), t.get('sentiment'), t.get('polarity')])
    mem = io.BytesIO()
    mem.write(si.getvalue().encode('utf-8'))
    mem.seek(0)
    filename = f"event_{event_id}_data.csv"
    return send_file(mem, as_attachment=True, download_name=filename, mimetype='text/csv')

@app.route('/export/pdf/<event_id>')
def export_pdf(event_id):
    """Export event summary as PDF"""
    ev = get_event(event_id)
    if not ev:
        flash("Event not found", "danger")
        return redirect(url_for('index'))

    api_resp = app.test_client().get(url_for('api_metrics', event_id=event_id))
    data = api_resp.get_json()
    metrics = data.get("summary", {})
    
    filename = os.path.join(app.config['EXPORT_FOLDER'], f"event_{event_id}_summary.pdf")
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height-40, f"Event Analysis: {ev.get('name')}")
    
    c.setFont("Helvetica", 11)
    y = height-70
    c.drawString(40, y, f"Analyzed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    
    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Key Metrics:")
    
    y -= 20
    c.setFont("Helvetica", 11)
    for k, v in metrics.items():
        if k not in ["platform_breakdown"]:
            c.drawString(60, y, f"{k}: {v}")
            y -= 18

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Recommendations:")
    
    y -= 20
    c.setFont("Helvetica", 11)
    recommendations = get_recommendations(metrics)
    for rec in recommendations:
        c.drawString(60, y, f"• {rec}")
        y -= 18
        if y < 50:
            c.showPage()
            y = height - 40

    c.save()
    return send_file(filename, as_attachment=True, download_name=os.path.basename(filename))

def get_recommendations(metrics):
    """Generate recommendations based on metrics"""
    recs = []
    
    buzz_score = metrics.get('buzz_score', 0)
    during_polarity = metrics.get('during_polarity', 0)
    total = metrics.get('total', 0)
    during_count = metrics.get('during', 0)
    pre_count = metrics.get('pre', 0)
    
    # Volume recommendations
    if total < 50:
        recs.append("Low overall buzz. Consider broader keywords or hashtags.")
    elif total < 200:
        recs.append("Moderate buzz levels. Opportunities for amplification exist.")
    else:
        recs.append("Strong buzz volume detected. Maintain momentum with timely content.")
    
    # Sentiment recommendations
    if during_polarity < -0.3:
        recs.append("⚠️ Negative sentiment detected! Implement rapid response strategy.")
    elif during_polarity < 0:
        recs.append("Slight negative sentiment. Monitor feedback and address concerns.")
    elif during_polarity > 0.5:
        recs.append("Excellent positive sentiment! Amplify top-performing content.")
    else:
        recs.append("Balanced sentiment. Continue standard engagement practices.")
    
    # Engagement recommendations
    if during_count > pre_count * 2:
        recs.append("Event generated significant surge in mentions. Capitalize on momentum.")
    elif during_count < pre_count:
        recs.append("Event didn't increase buzz. Review promotion strategy.")
    
    # Buzz score
    if buzz_score >= 75:
        recs.append(f"Buzz Score: {buzz_score}/100 - Viral potential detected!")
    elif buzz_score >= 50:
        recs.append(f"Buzz Score: {buzz_score}/100 - Good engagement levels.")
    else:
        recs.append(f"Buzz Score: {buzz_score}/100 - Focus on increasing visibility.")
    
    return recs

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
