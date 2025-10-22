window.renderCharts = function(timeseries) {
  if (!timeseries || !timeseries.times) {
    console.warn("Invalid timeseries data");
    return;
  }

  // Create label strings instead of Date objects for simpler handling
  const labels = timeseries.times.map(t => {
    const d = new Date(t);
    return d.toLocaleString('en-US', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  });

  // --- Volume Chart ---
  const volumeCtx = document.getElementById("volumeChart");
  if (!volumeCtx) {
    console.warn("volumeChart element not found");
    return;
  }
  
  // Destroy previous chart instance if it exists
  if (window.volumeChartInstance) {
    window.volumeChartInstance.destroy();
  }

  const ctx = volumeCtx.getContext("2d");
  window.volumeChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Buzz Volume',
        data: timeseries.counts || [],
        borderColor: '#3498db',
        backgroundColor: 'rgba(52, 152, 219, 0.1)',
        tension: 0.3,
        fill: true,
        borderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: '#3498db'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: true, position: 'top' },
        tooltip: { 
          mode: 'index',
          intersect: false,
          backgroundColor: 'rgba(0,0,0,0.8)',
          titleColor: '#fff',
          bodyColor: '#fff'
        }
      },
      scales: {
        x: { 
          display: true,
          title: { display: true, text: 'Time' },
          ticks: { maxRotation: 45, minRotation: 0 }
        },
        y: { 
          beginAtZero: true,
          title: { display: true, text: 'Mentions' }
        }
      }
    }
  });

  // --- Sentiment Chart ---
  const sentimentCtx = document.getElementById("sentimentChart");
  if (!sentimentCtx) {
    console.warn("sentimentChart element not found");
    return;
  }

  if (window.sentimentChartInstance) {
    window.sentimentChartInstance.destroy();
  }

  const sctx = sentimentCtx.getContext("2d");
  window.sentimentChartInstance = new Chart(sctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        { 
          label: 'Positive', 
          data: timeseries.positive || [], 
          borderColor: '#27ae60',
          backgroundColor: 'rgba(39, 174, 96, 0.1)',
          tension: 0.3,
          fill: true,
          borderWidth: 2,
          pointRadius: 3
        },
        { 
          label: 'Neutral', 
          data: timeseries.neutral || [], 
          borderColor: '#f39c12',
          backgroundColor: 'rgba(243, 156, 18, 0.1)',
          tension: 0.3,
          fill: true,
          borderWidth: 2,
          pointRadius: 3
        },
        { 
          label: 'Negative', 
          data: timeseries.negative || [], 
          borderColor: '#e74c3c',
          backgroundColor: 'rgba(231, 76, 60, 0.1)',
          tension: 0.3,
          fill: true,
          borderWidth: 2,
          pointRadius: 3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: true, position: 'top' },
        tooltip: { 
          mode: 'index',
          intersect: false,
          backgroundColor: 'rgba(0,0,0,0.8)',
          titleColor: '#fff',
          bodyColor: '#fff'
        }
      },
      scales: {
        x: { 
          display: true,
          title: { display: true, text: 'Time' },
          ticks: { maxRotation: 45, minRotation: 0 }
        },
        y: { 
          beginAtZero: true,
          stacked: false,
          title: { display: true, text: 'Sentiment Count' }
        }
      }
    }
  });
};
