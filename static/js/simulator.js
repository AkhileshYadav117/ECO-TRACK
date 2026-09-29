/**
 * EcoTrack — simulator.js
 * What-If Carbon Reduction Simulator on the Dashboard.
 *
 * Reads current user_type from localStorage and passes
 * it as a query param to /api/simulate so the backend
 * uses the correct monthly baseline:
 *
 *   Individual: monthly record total is the baseline
 *   Industry:   current month's aggregated daily total is the baseline
 *
 * The simulator does NOT write any records to the database.
 * It is a hypothetical "what-if" calculation only.
 */

document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('simulate-btn');
  if (!btn) return;
  btn.addEventListener('click', runSimulation);
});

async function runSimulation() {
  const userType = localStorage.getItem('ecotrack_user_type') || 'individual';

  const transportMode = document.getElementById('sim-transport-mode')?.value;
  const distanceKm    = document.getElementById('sim-distance')?.value    || 0;
  const electricityKwh= document.getElementById('sim-electricity')?.value || 0;
  const lpgCylinders  = document.getElementById('sim-lpg')?.value         || 0;
  const wasteKg       = document.getElementById('sim-waste')?.value       || 0;

  if (!transportMode) {
    showAlert('Please select a transport mode for the simulation.', 'error');
    return;
  }

  const payload = {
    transport_mode:  transportMode,
    distance_km:     distanceKm,
    electricity_kwh: electricityKwh,
    lpg_cylinders:   lpgCylinders,
    waste_kg:        wasteKg,
  };

  try {
    const res    = await fetch(`/api/simulate?user_type=${userType}`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload)
    });
    const result = await res.json().catch(() => ({}));

    if (!res.ok) {
      showAlert(result.error || 'Simulation failed.', 'error');
      return;
    }

    displaySimResult(result, userType);

  } catch (err) {
    showAlert('Network error during simulation. Is the server running?', 'error');
    console.error('Simulation error:', err);
  }
}

function displaySimResult(result, userType) {
  const simResult = document.getElementById('sim-result');
  if (!simResult) return;

  simResult.style.display = 'block';

  // For Industry, app.py returns projected_monthly (daily × 30 projection)
  const currentDisplay   = userType === 'industry' && result.current_monthly != null
    ? result.current_monthly
    : result.current_total;

  const projectedDisplay = userType === 'industry' && result.projected_monthly != null
    ? result.projected_monthly
    : result.simulated_total;

  const saving    = currentDisplay - projectedDisplay;
  const savingPct = currentDisplay > 0
    ? ((saving / currentDisplay) * 100).toFixed(1)
    : 0;

  document.getElementById('sim-original').textContent  = `${fmt(currentDisplay)} kg`;
  document.getElementById('sim-projected').textContent = `${fmt(projectedDisplay)} kg`;
  document.getElementById('sim-saving').textContent    = saving >= 0
    ? `−${fmt(saving)} kg (${savingPct}%)`
    : `+${fmt(Math.abs(saving))} kg`;

  // Update label if Industry (showing monthly projection)
  if (userType === 'industry') {
    const labels = simResult.querySelectorAll('[style*="color:var(--text-muted)"]');
    if (labels[0]) labels[0].textContent = 'Current Monthly Total';
    if (labels[1]) labels[1].textContent = 'Projected Monthly (×30 days)';
    if (labels[2]) labels[2].textContent = 'Monthly Saving';
  }
}
