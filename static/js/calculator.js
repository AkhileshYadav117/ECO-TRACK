/**
 * EcoTrack — calculator.js
 * Handles dual-mode carbon calculator.
 *
 * Individual / Household:
 *   - Monthly inputs (month, monthly km, kWh, cylinders, waste_kg)
 *   - POSTs user_type='individual' to /api/calculate
 *
 * Industry / Factory:
 *   - Daily inputs (date, daily km, kWh, cylinders, waste_kg)
 *   - POSTs user_type='industry' to /api/calculate
 *
 * Selected mode is persisted in localStorage ('ecotrack_user_type').
 */

let currentUserType = localStorage.getItem('ecotrack_user_type') || 'individual';

document.addEventListener('DOMContentLoaded', () => {
  // Restore last-used mode
  selectMode(currentUserType, false);

  // Set default date to today (Industry form)
  const dateInput = document.getElementById('ind-date');
  if (dateInput && !dateInput.value) {
    const today = new Date();
    const y = today.getFullYear();
    const m = String(today.getMonth() + 1).padStart(2, '0');
    const d = String(today.getDate()).padStart(2, '0');
    dateInput.value = `${y}-${m}-${d}`;
  }

  // Set default month to current month (Individual form)
  const monthInput = document.getElementById('ind-month');
  if (monthInput && !monthInput.value) {
    const today = new Date();
    const y = today.getFullYear();
    const m = String(today.getMonth() + 1).padStart(2, '0');
    monthInput.value = `${y}-${m}`;
  }

  // Attach form submit handlers
  document.getElementById('form-individual').addEventListener('submit', (e) => {
    e.preventDefault();
    submitCalculator('individual');
  });

  document.getElementById('form-industry').addEventListener('submit', (e) => {
    e.preventDefault();
    submitCalculator('industry');
  });
});


// ============================================================
// MODE SELECTION
// ============================================================

function selectMode(userType, scroll = true) {
  currentUserType = userType;
  localStorage.setItem('ecotrack_user_type', userType);

  // Update mode cards
  document.getElementById('mode-individual').classList.toggle('active', userType === 'individual');
  document.getElementById('mode-industry').classList.toggle('active',   userType === 'industry');

  // Show / hide form panels
  document.getElementById('panel-individual').classList.toggle('visible', userType === 'individual');
  document.getElementById('panel-industry').classList.toggle('visible',   userType === 'industry');

  // Hide result panel when switching modes
  const panel = document.getElementById('result-panel');
  if (panel) panel.style.display = 'none';
  clearAlert();

  if (scroll) {
    const formPanel = document.getElementById(`panel-${userType}`);
    if (formPanel) formPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}


// ============================================================
// FORM SUBMISSION
// ============================================================

async function submitCalculator(userType) {
  clearAlert();

  const btnId     = userType === 'individual' ? 'ind-calc-btn'     : 'ind-calc-btn-industry';
  const spinnerId = userType === 'individual' ? 'ind-spinner'       : 'ind-spinner-industry';
  const btn       = document.getElementById(btnId);
  const spinner   = document.getElementById(spinnerId);

  // Build payload based on mode
  let payload = { user_type: userType };

  if (userType === 'individual') {
    const month = document.getElementById('ind-month').value;
    const mode  = document.getElementById('ind-transport-mode').value;
    const dist  = document.getElementById('ind-distance').value;
    const elec  = document.getElementById('ind-electricity').value;
    const lpg   = document.getElementById('ind-lpg').value;
    const waste = document.getElementById('ind-waste').value;

    if (!month) { showAlert('Please select the billing month.', 'error'); return; }
    if (!mode)  { showAlert('Please select your transport mode.', 'error'); return; }

    payload = { ...payload, month, transport_mode: mode,
                distance_km: dist, electricity_kwh: elec,
                lpg_cylinders: lpg, waste_kg: waste };

  } else {
    const date  = document.getElementById('ind-date').value;
    const mode  = document.getElementById('ind-transport-mode-industry').value;
    const dist  = document.getElementById('ind-distance-industry').value;
    const elec  = document.getElementById('ind-electricity-industry').value;
    const lpg   = document.getElementById('ind-lpg-industry').value;
    const waste = document.getElementById('ind-waste-industry').value;

    if (!date) { showAlert('Please select the activity date.', 'error'); return; }
    if (!mode) { showAlert('Please select your transport mode.', 'error'); return; }

    payload = { ...payload, date, transport_mode: mode,
                distance_km: dist, electricity_kwh: elec,
                lpg_cylinders: lpg, waste_kg: waste };
  }

  // Loading state
  if (btn) btn.disabled = true;
  if (spinner) spinner.classList.add('visible');

  try {
    const response = await fetch('/api/calculate', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload)
    });

    const result = await response.json().catch(() => ({}));

    if (!response.ok) {
      showAlert(result.error || `Server error (${response.status}). Check terminal for details.`, 'error');
      return;
    }

    displayResult(result, userType);
    showAlert(
      userType === 'individual'
        ? 'Monthly footprint calculated and saved!'
        : 'Daily footprint calculated and saved!',
      'success'
    );

  } catch (err) {
    showAlert('Network error — make sure Flask is running on port 5000.', 'error');
    console.error('Fetch error:', err);
  } finally {
    if (btn) btn.disabled = false;
    if (spinner) spinner.classList.remove('visible');
  }
}


// ============================================================
// RESULT DISPLAY
// ============================================================

function displayResult(result, userType) {
  const panel = document.getElementById('result-panel');
  if (!panel) return;

  panel.style.display = 'block';
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

  // Period label and icon
  const iconEl   = document.getElementById('result-icon');
  const periodEl = document.getElementById('result-period-label');
  const dateEl   = document.getElementById('result-date-label');

  if (userType === 'individual') {
    if (iconEl)   iconEl.textContent   = '🏠';
    if (periodEl) periodEl.textContent = 'Monthly Carbon Footprint';
    if (dateEl && result.month) {
      const d = new Date(result.month + '-01');
      dateEl.textContent = `for ${d.toLocaleDateString('en-IN', { year: 'numeric', month: 'long' })}`;
    }
  } else {
    if (iconEl)   iconEl.textContent   = '🏭';
    if (periodEl) periodEl.textContent = 'Daily Carbon Footprint';
    if (dateEl && result.date) {
      const d = new Date(result.date + 'T00:00:00');
      dateEl.textContent = `for ${d.toLocaleDateString('en-IN', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
      })}`;
    }
  }

  // Total
  document.getElementById('result-total-value').textContent = fmt(result.total);

  // Breakdown
  document.getElementById('r-transport').textContent   = fmt(result.transport);
  document.getElementById('r-electricity').textContent = fmt(result.electricity);
  document.getElementById('r-fuel').textContent        = fmt(result.fuel);
  document.getElementById('r-waste').textContent       = fmt(result.waste);

  // Quality badge
  const qBadge = document.getElementById('quality-badge');
  if (qBadge && result.data_quality) {
    qBadge.outerHTML = qualityBadgeHTML(result.data_quality);
  }

  // Quality notes
  const notesEl = document.getElementById('quality-notes-container');
  if (notesEl && result.quality_notes && result.quality_notes.length > 0) {
    const items = result.quality_notes.map(n => `<li style="margin-bottom:0.3rem;">${n}</li>`).join('');
    notesEl.innerHTML = `
      <div class="alert alert-info" style="margin-top:0.5rem;">
        <strong>Quality Notes:</strong>
        <ul style="margin-top:0.4rem; padding-left:1.2rem;">${items}</ul>
      </div>`;
  } else if (notesEl) {
    notesEl.innerHTML = '';
  }

  // Anomaly warning
  const anomalyDiv = document.getElementById('anomaly-warning');
  if (anomalyDiv) {
    anomalyDiv.style.display = result.is_anomaly ? 'block' : 'none';
    if (result.is_anomaly) {
      const msg = document.getElementById('anomaly-message');
      if (msg) msg.textContent = result.anomaly_message || 'Unusual value detected. Please verify.';
    }
  }

  // Update saved message
  const savedMsg = document.getElementById('result-saved-msg');
  if (savedMsg) {
    savedMsg.innerHTML = userType === 'individual'
      ? `✅ Monthly record saved. Visit the <a href="/dashboard?user_type=individual" style="color:var(--accent);">Dashboard</a> to view your data.`
      : `✅ Daily record saved. Records accumulate into monthly totals on the <a href="/dashboard?user_type=industry" style="color:var(--accent);">Dashboard</a>.`;
  }
}
