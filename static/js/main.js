document.addEventListener("DOMContentLoaded", function(){
  const startBtn = document.getElementById("startCollectionBtn");
  const loading = document.getElementById("loading");

  function showLoading() { 
    if (loading) loading.style.display = ""; 
  }
  
  function hideLoading() { 
    if (loading) loading.style.display = "none"; 
  }

  async function fetchMetrics(){
    showLoading();
    try {
      const r = await fetch(`/api/metrics/${EVENT_ID}`);
      if (!r.ok) {
        throw new Error(`HTTP error! status: ${r.status}`);
      }
      const data = await r.json();
      hideLoading();
      
      if (window.renderCharts) {
        window.renderCharts(data.timeseries);
      }
      renderSummary(data.summary);
    } catch(e){
      hideLoading();
      console.error("Error fetching metrics:", e);
      const recDiv = document.getElementById("recommendations");
      if (recDiv) {
        recDiv.innerHTML = `<div class="alert alert-danger" role="alert">Error loading metrics: ${e.message}</div>`;
      }
    }
  }

  startBtn && startBtn.addEventListener("click", async function(){
    startBtn.disabled = true;
    const originalText = startBtn.innerHTML;
    startBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Starting...';
    try {
      const r = await fetch(`/start_collection/${EVENT_ID}`, {method: "POST"});
      const j = await r.json();
      if (j.status === "started") {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-dismissible fade show';
        alert.innerHTML = `
          <strong>Analysis Started!</strong> Data collection from Reddit, YouTube, and News is now running in the background. 
          This may take a few minutes. Refresh the page to see updated metrics.
          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        const container = document.querySelector('.container-fluid');
        if (container) container.insertBefore(alert, container.firstChild);
        
        // Auto-refresh every 10 seconds
        setTimeout(() => {
          fetchMetrics();
        }, 5000);
      } else {
        alert("Error: " + JSON.stringify(j));
      }
    } catch(e){
      console.error("Failed to start collection:", e);
      alert("Failed to start analysis: " + e.message);
    } finally {
      startBtn.disabled = false;
      startBtn.innerHTML = originalText;
      fetchMetrics();
    }
  });

  function renderSummary(s) {
    if (!s) return;
    
    // Update individual metric badges
    const metrics = {
      'total': s.total || 0,
      'pre': s.pre || 0,
      'during': s.during || 0,
      'post': s.post || 0,
      'pos': s.pos || 0,
      'neu': s.neu || 0,
      'neg': s.neg || 0
    };

    for (const [key, value] of Object.entries(metrics)) {
      const elem = document.getElementById(`metric-${key}`);
      if (elem) elem.textContent = value;
    }

    // Update buzz score
    const buzzScore = s.buzz_score || 0;
    const buzzScoreElem = document.getElementById("buzzScore");
    if (buzzScoreElem) {
      buzzScoreElem.textContent = buzzScore;
      buzzScoreElem.style.fontSize = '3em';
      buzzScoreElem.style.fontWeight = 'bold';
      
      if (buzzScore >= 75) {
        buzzScoreElem.style.color = '#27ae60';
      } else if (buzzScore >= 50) {
        buzzScoreElem.style.color = '#f39c12';
      } else {
        buzzScoreElem.style.color = '#e74c3c';
      }
    }

    // Update buzz interpretation
    const interpretation = document.getElementById("buzzInterpretation");
    if (interpretation) {
      if (buzzScore >= 75) {
        interpretation.textContent = '🔥 Viral! Massive engagement detected.';
        interpretation.style.color = '#27ae60';
      } else if (buzzScore >= 50) {
        interpretation.textContent = '👍 Good buzz! Solid engagement levels.';
        interpretation.style.color = '#f39c12';
      } else if (buzzScore > 0) {
        interpretation.textContent = '📊 Moderate buzz. Room for growth.';
        interpretation.style.color = '#3498db';
      } else {
        interpretation.textContent = '😴 Low buzz. Boost visibility.';
        interpretation.style.color = '#95a5a6';
      }
    }

    // Update polarity progress bars
    const polarities = {
      'pre': s.pre_polarity || 0,
      'during': s.during_polarity || 0,
      'post': s.post_polarity || 0
    };

    for (const [period, polarity] of Object.entries(polarities)) {
      const elem = document.getElementById(`polarity-${period}`);
      if (elem) {
        const percentage = Math.round((polarity + 1) / 2 * 100);
        elem.style.width = percentage + '%';
        
        // Apply color styling
        elem.className = 'progress-bar';
        if (polarity < -0.3) {
          elem.className += ' bg-danger';
        } else if (polarity < -0.1) {
          elem.className += ' bg-danger';
        } else if (polarity < 0.1) {
          elem.className += ' bg-warning';
        } else if (polarity < 0.3) {
          elem.className += ' bg-info';
        } else {
          elem.className += ' bg-success';
        }
        
        elem.textContent = formatPolarity(polarity);
      }
    }

    // Render recommendations
    renderRecommendations(s);
  }

  function formatPolarity(val) {
    if (val === null || val === undefined) return "N/A";
    const percentage = Math.round((val + 1) / 2 * 100);
    return percentage + "%";
  }

  function renderRecommendations(s) {
    const rec = document.getElementById("recommendations");
    if (!rec) return;
    
    rec.innerHTML = "";
    const recommendations = getRecommendations(s);
    
    recommendations.forEach(text => {
      const div = document.createElement("div");
      div.className = "list-group-item";
      div.innerHTML = text;
      rec.appendChild(div);
    });
  }

  function getRecommendations(s) {
    const recs = [];
    
    const buzzScore = s.buzz_score || 0;
    const duringPolarity = s.during_polarity || 0;
    const total = s.total || 0;
    const duringCount = s.during || 0;
    const preCount = s.pre || 0;

    // Volume recommendations
    if (total < 50) {
      recs.push('<i class="fas fa-arrow-up text-warning"></i> <strong>Low buzz detected.</strong> Consider broader keywords, hashtags, or platform expansion.');
    } else if (total < 200) {
      recs.push('<i class="fas fa-chart-line text-info"></i> <strong>Moderate buzz levels.</strong> Opportunities exist for amplification and engagement boosts.');
    } else {
      recs.push('<i class="fas fa-star text-success"></i> <strong>Strong buzz volume!</strong> Maintain momentum with timely, high-quality content.');
    }

    // Sentiment recommendations
    if (duringPolarity < -0.3) {
      recs.push('<i class="fas fa-exclamation-triangle text-danger"></i> <strong>⚠️ Significant negative sentiment detected!</strong> Implement rapid response and monitoring strategy immediately.');
    } else if (duringPolarity < 0) {
      recs.push('<i class="fas fa-eye text-warning"></i> <strong>Slight negative sentiment observed.</strong> Monitor feedback closely and address concerns proactively.');
    } else if (duringPolarity > 0.5) {
      recs.push('<i class="fas fa-thumbs-up text-success"></i> <strong>Excellent positive sentiment!</strong> Amplify top-performing content and identify influencers for amplification.');
    } else {
      recs.push('<i class="fas fa-balance-scale text-info"></i> <strong>Balanced sentiment mix.</strong> Continue standard engagement and monitoring practices.');
    }

    // Engagement recommendations
    if (duringCount > preCount * 2) {
      recs.push('<i class="fas fa-rocket text-success"></i> <strong>Event drove significant surge!</strong> Capitalize on momentum with time-sensitive promotions and influencer partnerships.');
    } else if (duringCount < preCount) {
      recs.push('<i class="fas fa-chart-bar text-warning"></i> <strong>Event didn\'t boost mentions as expected.</strong> Review marketing strategy and consider channel expansion.');
    } else {
      recs.push('<i class="fas fa-plus-circle text-info"></i> <strong>Steady engagement maintained.</strong> Keep promoting to sustain and grow buzz further.');
    }

    // Buzz score interpretation
    if (buzzScore >= 75) {
      recs.push('<i class="fas fa-fire text-danger"></i> <strong>🔥 Buzz Score: ' + buzzScore + '/100 - VIRAL!</strong> This event has exceptional viral potential. Focus on capturing and sustaining engagement.');
    } else if (buzzScore >= 50) {
      recs.push('<i class="fas fa-smile text-warning"></i> <strong>Buzz Score: ' + buzzScore + '/100 - Good engagement.</strong> Solid performance with room for optimization.');
    } else if (buzzScore > 0) {
      recs.push('<i class="fas fa-info-circle text-muted"></i> <strong>Buzz Score: ' + buzzScore + '/100 - Moderate engagement.</strong> Focus on visibility and reach expansion.');
    } else {
      recs.push('<i class="fas fa-ban text-secondary"></i> <strong>Buzz Score: ' + buzzScore + '/100 - Low engagement.</strong> Significant effort needed to increase awareness.');
    }

    // Platform-specific recommendations
    if (s.platform_breakdown) {
      const topPlatform = Object.keys(s.platform_breakdown).reduce((a, b) => 
        s.platform_breakdown[a] > s.platform_breakdown[b] ? a : b, 'unknown');
      recs.push('<i class="fas fa-globe text-primary"></i> <strong>Top platform: ' + topPlatform.charAt(0).toUpperCase() + topPlatform.slice(1) + '.</strong> Focus content strategy around this channel.');
    }

    return recs;
  }

  // Initial fetch on page load
  fetchMetrics();
  
  // Auto-refresh every 30 seconds
  setInterval(fetchMetrics, 30000);
});
