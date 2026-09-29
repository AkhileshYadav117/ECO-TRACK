/**
 * EcoTrack — dashboard.js
 * Loads dashboard data for both Individual and Industry modes.
 *
 * Individual:
 *   Monthly records are the source of truth.
 *   /api/monthly-summary?user_type=individual
 *
 * Industry:
 *   Daily records aggregated to monthly.
 *   /api/monthly-summary?user_type=industry
 *   /api/daily-summary     (for daily trend chart)
 *
 * Mode is read from localStorage ('ecotrack_user_type').
 * The mode toggle also stores back to localStorage.
 */

let trendChart      = null;
let donutChart      = null;
let dailyTrendChart = null;
let dashUserType    = localStorage.getItem('ecotrack_user_type') || 'individual';

document.addEventListener('DOMContentLoaded', () => {
  // Apply mode from localStorage (may also come from URL ?user_type=)
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has('user_type')) {
    dashUserType = urlParams.get('user_type');
    localStorage.setItem('ecotrack_user_type', dashUserType);
  }

  applyModeUI(dashUserType);
  loadAll(dashUserType);
  setupGoalForm();
});


// ============================================================
// MODE SWITCHING
// ============================================================

function switchDashMode(userType) {
  dashUserType = userType;
  localStorage.setItem('ecotrack_user_type', userType);
  applyModeUI(userType);
  loadAll(userType);
}

function applyModeUI(userType) {
  // Toggle buttons
  document.getElementById('dash-btn-individual').classList.toggle('active', userType === 'individual');
  document.getElementById('dash-btn-industry').classList.toggle('active',   userType === 'industry');

  // Show/hide industry-only sections
  document.querySelectorAll('.industry-only').forEach(el => {
    el.style.display = userType === 'industry' ? '' : 'none';
  });

  // Update stat card label
  const label = document.getElementById('stat-current-label');
  if (label) label.textContent = userType === 'individual' ? 'This Month' : 'This Month (Aggregated)';
}


// ============================================================
// LOAD ALL DASHBOARD DATA
// ============================================================

function loadAll(userType) {
  loadMonthlySummary(userType);
  loadRecommendations(userType);
  loadMLPrediction(userType);
  loadGoal(userType);
  if (userType === 'industry') loadDailyTrend();
}


// ============================================================
// MONTHLY SUMMARY — Stat Cards + Charts
// ============================================================

async function loadMonthlySummary(userType) {
  try {
    const res  = await fetch(`/api/monthly-summary?user_type=${userType}`);
    const data = await res.json();

    const summaries = data.summaries || [];
    const current   = data.current;
    const previous  = data.previous;
    const change    = data.change;

    // ---- Stat Cards ----
    document.getElementById('stat-current').textContent  = current  ? fmt(current.total)  : '—';
    document.getElementById('stat-previous').textContent = previous ? fmt(previous.total) : '—';

    if (change && Object.keys(change).length > 0) {
      const sign = change.absolute > 0 ? '+' : '';
      const changeEl = document.getElementById('stat-change');
      if (changeEl) {
        changeEl.textContent = `${sign}${fmt(change.absolute)}`;
        changeEl.className   = `stat-value ${change.direction}`;
      }
      const pctEl = document.getElementById('stat-change-pct');
      if (pctEl) pctEl.textContent = `${sign}${change.percent}% vs last month`;

      const labelEl = document.getElementById('stat-change-label');
      if (labelEl) {
        labelEl.textContent = change.direction === 'up'
          ? '↑ Footprint increased' : '↓ Footprint decreased';
        labelEl.className = `stat-change ${change.direction}`;
      }
    } else {
      document.getElementById('stat-change').textContent = '—';
    }

    // Industry extra stats
    if (userType === 'industry' && current) {
      const avgEl  = document.getElementById('stat-daily-avg');
      const daysEl = document.getElementById('stat-days');
      if (avgEl)  avgEl.textContent  = current.daily_avg != null ? fmt(current.daily_avg) : '—';
      if (daysEl) daysEl.textContent = current.day_count || 0;
    }

    // ---- Charts ----
    if (summaries.length >= 1) {
      renderTrendChart(summaries, userType);
      renderDonutChart(current || summaries[summaries.length - 1]);
      document.getElementById('trend-empty').style.display = 'none';
      document.getElementById('donut-empty').style.display = 'none';
    } else {
      document.getElementById('trend-empty').style.display = 'block';
      document.getElementById('donut-empty').style.display = 'block';
    }

  } catch (err) {
    console.error('Monthly summary error:', err);
  }
}


// ============================================================
// CHARTS
// ============================================================

function renderTrendChart(summaries, userType) {
  const canvas = document.getElementById('trend-chart');
  if (!canvas) return;
  if (trendChart) trendChart.destroy();

  const titleEl = document.getElementById('trend-chart-title');
  if (titleEl) titleEl.textContent = userType === 'individual'
    ? 'Monthly Footprint Trend' : 'Monthly Aggregated Footprint Trend';

  const labels = summaries.map(s => s.month);
  const totals = summaries.map(s => parseFloat(s.total.toFixed(1)));

  trendChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Monthly CO₂e (kg)',
        data: totals,
        borderColor:          '#22c55e',
        backgroundColor:      'rgba(34,197,94,0.08)',
        pointBackgroundColor: '#22c55e',
        pointRadius: 5,
        tension: 0.4,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: '#94a3b8', font: { family: 'Inter' } } },
        tooltip: { callbacks: { label: ctx => ` ${ctx.parsed.y.toFixed(1)} kg CO₂e` } }
      },
      scales: {
        x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: {
          ticks: { color: '#64748b' },
          grid: { color: 'rgba(255,255,255,0.05)' },
          title: { display: true, text: 'kg CO₂e (Monthly)', color: '#64748b' }
        }
      }
    }
  });
}

function renderDonutChart(record) {
  const canvas = document.getElementById('donut-chart');
  if (!canvas || !record) return;
  if (donutChart) donutChart.destroy();

  donutChart = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: ['Transport', 'Electricity', 'Fuel', 'Waste'],
      datasets: [{
        data: [
          parseFloat((record.transport   || 0).toFixed(1)),
          parseFloat((record.electricity || 0).toFixed(1)),
          parseFloat((record.fuel        || 0).toFixed(1)),
          parseFloat((record.waste       || 0).toFixed(1)),
        ],
        backgroundColor: ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444'],
        borderColor: 'rgba(0,0,0,0)',
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', font: { family: 'Inter' }, padding: 12 }
        },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed.toFixed(1)} kg CO₂e` } }
      }
    }
  });
}


// ============================================================
// INDUSTRY DAILY TREND CHART
// ============================================================

async function loadDailyTrend() {
  try {
    const res  = await fetch('/api/daily-summary');
    const data = await res.json();
    const records = data.records || [];

    if (records.length === 0) {
      document.getElementById('daily-trend-empty').style.display = 'block';
      return;
    }
    document.getElementById('daily-trend-empty').style.display = 'none';

    renderDailyTrendChart(records);
  } catch (err) {
    console.error('Daily trend error:', err);
  }
}

function renderDailyTrendChart(records) {
  const canvas = document.getElementById('daily-trend-chart');
  if (!canvas) return;
  if (dailyTrendChart) dailyTrendChart.destroy();

  const labels = records.map(r => r.date);
  const totals = records.map(r => parseFloat(r.total.toFixed(1)));

  dailyTrendChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Daily CO₂e (kg)',
        data: totals,
        backgroundColor: totals.map(v => {
          const avg = totals.reduce((a, b) => a + b, 0) / totals.length;
          return v > avg * 1.5 ? 'rgba(239,68,68,0.7)' : 'rgba(34,197,94,0.55)';
        }),
        borderRadius: 4,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: '#94a3b8', font: { family: 'Inter' } } },
        tooltip: { callbacks: { label: ctx => ` ${ctx.parsed.y.toFixed(1)} kg CO₂e` } }
      },
      scales: {
        x: { ticks: { color: '#64748b', maxTicksLimit: 15 }, grid: { color: 'rgba(255,255,255,0.03)' } },
        y: {
          ticks: { color: '#64748b' },
          grid:  { color: 'rgba(255,255,255,0.05)' },
          title: { display: true, text: 'kg CO₂e (Daily)', color: '#64748b' }
        }
      }
    }
  });
}


// ============================================================
// RECOMMENDATIONS
// ============================================================

async function loadRecommendations(userType) {
  const container = document.getElementById('recommendations-container');
  if (!container) return;

  try {
    const res  = await fetch(`/api/recommendations?user_type=${userType}`);
    const data = await res.json();

    if (!data.recommendations || data.recommendations.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">💡</div>
          <h3>No recommendations yet</h3>
          <p>Add at least one ${userType === 'individual' ? 'monthly' : 'daily'} entry to get tips.</p>
        </div>`;
      return;
    }

    const items = data.recommendations.map(r => `
      <div style="display:flex; gap:10px; align-items:flex-start;
                  padding:0.6rem 0; border-bottom:1px solid var(--border);">
        <span style="color:var(--accent); flex-shrink:0;">🌱</span>
        <span style="font-size:0.875rem; color:var(--text-secondary);">${r}</span>
      </div>`).join('');

    container.innerHTML = `
      <div class="alert alert-info" style="margin-bottom:1rem;">
        Highest emission category: <strong>${(data.dominant_category || '').toUpperCase()}</strong>
      </div>
      ${items}`;

  } catch (err) {
    container.innerHTML = `<div class="alert alert-error">Failed to load recommendations.</div>`;
  }
}


// ============================================================
// ML PREDICTION
// ============================================================

async function loadMLPrediction(userType) {
  const container = document.getElementById('ml-prediction-container');
  const statEl    = document.getElementById('stat-prediction');
  const noteEl    = document.getElementById('stat-prediction-note');
  if (!container) return;

  try {
    const res  = await fetch(`/api/predict?user_type=${userType}`);
    const data = await res.json();

    if (data.status === 'insufficient_data') {
      container.innerHTML = `
        <div class="alert alert-warning">
          <strong>Insufficient Monthly History</strong><br/>${data.message}
        </div>`;
      if (statEl) statEl.textContent = '—';
      if (noteEl) noteEl.textContent = 'Need 3+ months';
      return;
    }

    if (data.status === 'success') {
      const pred = parseFloat(data.predicted_co2e).toFixed(1);
      if (statEl) statEl.textContent = pred;

      const modeNote = userType === 'industry'
        ? 'Daily records are aggregated into monthly totals, then used for ML prediction.'
        : 'Monthly records are used directly for ML prediction.';

      container.innerHTML = `
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr;
                    gap:1rem; text-align:center; margin-bottom:1rem;">
          <div>
            <div style="font-size:2rem; font-weight:800; color:var(--accent-light);">${pred}</div>
            <div style="font-size:0.78rem; color:var(--text-muted);">Predicted kg CO₂e</div>
          </div>
          <div>
            <div style="font-size:1.2rem; font-weight:700; color:var(--text-secondary);">
              ${data.model || 'Linear Regression'}
            </div>
            <div style="font-size:0.78rem; color:var(--text-muted);">Model</div>
          </div>
          <div>
            <div style="font-size:2rem; font-weight:800; color:var(--text-secondary);">
              ${data.data_points || '—'}
            </div>
            <div style="font-size:0.78rem; color:var(--text-muted);">Months of Data</div>
          </div>
        </div>
        <div class="alert alert-info">${modeNote}</div>
        ${data.mae ? `<p style="font-size:0.78rem;color:var(--text-muted);margin-top:0.5rem;">
          Model MAE: ${parseFloat(data.mae).toFixed(2)} kg CO₂e</p>` : ''}`;
    }
  } catch (err) {
    if (container) container.innerHTML = `<div class="alert alert-error">Failed to load prediction.</div>`;
  }
}


// ============================================================
// GOALS
// ============================================================

function setupGoalForm() {
  const btn = document.getElementById('set-goal-btn');
  if (!btn) return;

  // Pre-fill current month
  const monthInput = document.getElementById('goal-month');
  if (monthInput && !monthInput.value) {
    const now = new Date();
    monthInput.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  }

  btn.addEventListener('click', async () => {
    const month  = document.getElementById('goal-month').value;
    const target = document.getElementById('goal-target').value;

    if (!month || !target || parseFloat(target) <= 0) {
      showAlert('Please enter a valid month and a positive target.', 'error');
      return;
    }

    try {
      const res  = await fetch(`/api/goals?user_type=${dashUserType}`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          user_type:   dashUserType,
          month,
          target_co2e: parseFloat(target)
        })
      });
      const data = await res.json();
      if (!res.ok) { showAlert(data.error || 'Failed to save goal.', 'error'); return; }
      showAlert('Goal saved!', 'success');
      loadGoal(dashUserType);
    } catch (err) {
      showAlert('Network error saving goal.', 'error');
    }
  });
}

async function loadGoal(userType) {
  try {
    const res  = await fetch(`/api/goals?user_type=${userType}`);
    const data = await res.json();
    if (!data.goal) return;

    const goal    = data.goal;
    const current = data.current_footprint || 0;
    const target  = goal.target_co2e;
    const pct     = Math.min((current / target) * 100, 100).toFixed(0);
    const days    = data.day_count || 0;

    document.getElementById('goal-form-section').style.display     = 'none';
    document.getElementById('goal-progress-section').style.display = 'block';
    document.getElementById('goal-current').textContent            = fmt(current);
    document.getElementById('goal-target-display').textContent     = fmt(target);
    document.getElementById('goal-progress-bar').style.width       = `${pct}%`;

    const remaining  = Math.max(target - current, 0).toFixed(1);
    const daysNote   = userType === 'industry' ? ` (${days} days recorded)` : '';
    document.getElementById('goal-status-text').textContent = current <= target
      ? `On track! ${remaining} kg below target.${daysNote}`
      : `Over target by ${(current - target).toFixed(1)} kg.${daysNote}`;

  } catch (err) {
    // No goal set — form shown by default
  }
}
