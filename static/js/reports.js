/**
 * EcoTrack — reports.js
 * History page: loads and displays footprint records.
 *
 * Individual mode:
 *   - Fetches /api/history?user_type=individual
 *   - Table shows: Month | Transport | Electricity | Fuel | Waste | Total | Quality | Flag
 *   - Summary stats: count, average monthly, highest, lowest
 *
 * Industry mode:
 *   - Fetches /api/history?user_type=industry
 *   - Table shows: Date | Month | Transport | Electricity | Fuel | Waste | Daily Total | Quality | Flag
 *   - Summary stats: total daily records, average daily, highest day, lowest day
 *
 * Mode persisted in localStorage ('ecotrack_user_type').
 */

let histUserType = localStorage.getItem('ecotrack_user_type') || 'individual';

document.addEventListener('DOMContentLoaded', () => {
  applyHistModeUI(histUserType);
  loadHistory(histUserType);
  setupExport();
});


// ============================================================
// MODE SWITCHING
// ============================================================

function switchHistMode(userType) {
  histUserType = userType;
  localStorage.setItem('ecotrack_user_type', userType);
  applyHistModeUI(userType);
  loadHistory(userType);
}

function applyHistModeUI(userType) {
  document.getElementById('hist-btn-individual').classList.toggle('active', userType === 'individual');
  document.getElementById('hist-btn-industry').classList.toggle('active',   userType === 'industry');

  const subtitle = document.getElementById('history-subtitle');
  if (subtitle) {
    subtitle.textContent = userType === 'individual'
      ? 'All your recorded monthly carbon footprint entries.'
      : 'All your recorded daily carbon footprint entries (Industry / Factory).';
  }

  const tableTitle = document.getElementById('table-title');
  if (tableTitle) {
    tableTitle.textContent = userType === 'individual'
      ? 'Monthly Records — Individual / Household'
      : 'Daily Records — Industry / Factory';
  }

  const summaryTitle = document.getElementById('summary-title');
  if (summaryTitle) summaryTitle.textContent = 'Historical Summary';

  // Update stat labels
  const avgLabel   = document.getElementById('avg-label');
  const maxLabel   = document.getElementById('max-label');
  const minLabel   = document.getElementById('min-label');
  const cntLabel   = document.getElementById('count-label');

  if (userType === 'individual') {
    if (cntLabel) cntLabel.textContent = 'Total Monthly Records';
    if (avgLabel) avgLabel.textContent = 'Average Monthly Footprint';
    if (maxLabel) maxLabel.textContent = 'Highest Month';
    if (minLabel) minLabel.textContent = 'Lowest Month';
  } else {
    if (cntLabel) cntLabel.textContent = 'Total Daily Records';
    if (avgLabel) avgLabel.textContent = 'Average Daily Footprint';
    if (maxLabel) maxLabel.textContent = 'Highest Day';
    if (minLabel) minLabel.textContent = 'Lowest Day';
  }
}


// ============================================================
// LOAD HISTORY
// ============================================================

async function loadHistory(userType) {
  // Reset table
  const container = document.getElementById('history-table-container');
  const empty     = document.getElementById('history-empty');
  if (container) container.style.display = 'none';
  if (empty)     empty.style.display     = 'block';

  try {
    const res  = await fetch(`/api/history?user_type=${userType}`);
    const data = await res.json();

    if (!data.records || data.records.length === 0) {
      if (empty) empty.style.display = 'block';
      if (container) container.style.display = 'none';
      resetSummary();
      return;
    }

    if (empty)     empty.style.display     = 'none';
    if (container) container.style.display = 'block';

    injectTableHeaders(userType);
    renderTable(data.records, userType);
    renderSummary(data.records, userType);

  } catch (err) {
    showAlert('Failed to load history. Is the server running?', 'error');
  }
}


// ============================================================
// TABLE HEADERS (injected dynamically per mode)
// ============================================================

function injectTableHeaders(userType) {
  const thead = document.getElementById('history-thead');
  if (!thead) return;

  if (userType === 'individual') {
    thead.innerHTML = `
      <tr>
        <th>Month</th>
        <th>Transport (kg CO₂e)</th>
        <th>Electricity (kg CO₂e)</th>
        <th>Fuel (kg CO₂e)</th>
        <th>Waste (kg CO₂e)</th>
        <th>Monthly Total</th>
        <th>Quality</th>
        <th>Flag</th>
      </tr>`;
  } else {
    thead.innerHTML = `
      <tr>
        <th>Date</th>
        <th>Month</th>
        <th>Transport (kg CO₂e)</th>
        <th>Electricity (kg CO₂e)</th>
        <th>Fuel (kg CO₂e)</th>
        <th>Waste (kg CO₂e)</th>
        <th>Daily Total</th>
        <th>Quality</th>
        <th>Flag</th>
      </tr>`;
  }
}


// ============================================================
// RENDER TABLE ROWS
// ============================================================

function renderTable(records, userType) {
  const tbody = document.getElementById('history-tbody');
  if (!tbody) return;

  // Show newest first
  const sorted = [...records].reverse();

  if (userType === 'individual') {
    tbody.innerHTML = sorted.map(r => {
      const anomaly = r.is_anomaly
        ? '<span style="color:var(--warning);">⚠️ Anomaly</span>' : '—';
      return `
        <tr>
          <td><strong>${r.month}</strong></td>
          <td>${fmt(r.transport)}</td>
          <td>${fmt(r.electricity)}</td>
          <td>${fmt(r.fuel)}</td>
          <td>${fmt(r.waste)}</td>
          <td><strong style="color:var(--accent-light);">${fmt(r.total)}</strong></td>
          <td>${qualityBadgeHTML(r.data_quality || 'Medium')}</td>
          <td>${anomaly}</td>
        </tr>`;
    }).join('');

  } else {
    tbody.innerHTML = sorted.map(r => {
      const anomaly = r.is_anomaly
        ? '<span style="color:var(--warning);">⚠️ Anomaly</span>' : '—';
      return `
        <tr>
          <td><strong>${r.date}</strong></td>
          <td style="color:var(--text-muted); font-size:0.82rem;">${r.month}</td>
          <td>${fmt(r.transport)}</td>
          <td>${fmt(r.electricity)}</td>
          <td>${fmt(r.fuel)}</td>
          <td>${fmt(r.waste)}</td>
          <td><strong style="color:var(--accent-light);">${fmt(r.total)}</strong></td>
          <td>${qualityBadgeHTML(r.data_quality || 'Medium')}</td>
          <td>${anomaly}</td>
        </tr>`;
    }).join('');
  }
}


// ============================================================
// SUMMARY STATS
// ============================================================

function renderSummary(records, userType) {
  const totals = records.map(r => r.total);
  const count  = totals.length;
  const avg    = totals.reduce((a, b) => a + b, 0) / count;
  const max    = Math.max(...totals);
  const min    = Math.min(...totals);

  document.getElementById('hist-count').textContent = count;
  document.getElementById('hist-avg').textContent   = fmt(avg);
  document.getElementById('hist-max').textContent   = fmt(max);
  document.getElementById('hist-min').textContent   = fmt(min);
}

function resetSummary() {
  ['hist-count', 'hist-avg', 'hist-max', 'hist-min'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = '—';
  });
}


// ============================================================
// CSV EXPORT
// ============================================================

function setupExport() {
  // Raw records CSV
  const btn = document.getElementById('export-csv-btn');
  if (btn) {
    btn.addEventListener('click', async () => {
      try {
        const res = await fetch(`/api/report?user_type=${histUserType}`);
        if (!res.ok) { showAlert('Export failed.', 'error'); return; }
        await downloadBlob(res,
          histUserType === 'individual'
            ? `ecotrack_individual_${today()}.csv`
            : `ecotrack_industry_daily_${today()}.csv`
        );
        showAlert('CSV exported!', 'success');
      } catch (err) {
        showAlert('Export failed. Network error.', 'error');
      }
    });
  }

  // Monthly aggregated CSV
  const monthBtn = document.getElementById('export-monthly-btn');
  if (monthBtn) {
    monthBtn.addEventListener('click', async () => {
      try {
        const res = await fetch(`/api/report/monthly?user_type=${histUserType}`);
        if (!res.ok) { showAlert('Export failed.', 'error'); return; }
        await downloadBlob(res,
          `ecotrack_${histUserType}_monthly_summary_${today()}.csv`
        );
        showAlert('Monthly summary CSV exported!', 'success');
      } catch (err) {
        showAlert('Export failed. Network error.', 'error');
      }
    });
  }
}

async function downloadBlob(res, filename) {
  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function today() {
  return new Date().toISOString().slice(0, 10);
}
