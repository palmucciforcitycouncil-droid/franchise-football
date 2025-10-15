// League Power Rankings widget with scrollable list
import { demoPR, withDemo } from './demoData.js';

const CARD = document.getElementById('power-card');
const DEMO = document.getElementById('power-demo');

export async function initPowerRankings(){
  if (!CARD) return;
  
  const { data, isDemo } = await withDemo(
    async (signal) => {
      const r = await fetch('/api/power-rankings', {
        headers: {'Accept': 'application/json'},
        signal
      });
      if (!r.ok) throw new Error('status ' + r.status);
      return r.json();
    },
    demoPR
  );
  
  if (isDemo) {
    showErrorBanner();
    DEMO.hidden = false;
  } else {
    DEMO.hidden = true;
  }
  
  renderPowerRankings(data);
}

function renderPowerRankings(data){
  const cardBody = CARD.querySelector('.card-body');
  if (!cardBody) return;
  
  const rankings = Array.isArray(data) ? data : [];
  
  cardBody.innerHTML = `
    <div class="power-header">
      <span class="subtitle">Top 5 (scroll to see all 32)</span>
    </div>
    <div class="power-scroll">
      <div class="power-list">
        ${rankings.map(row => powerRow(row)).join('')}
      </div>
    </div>
  `;
}

function powerRow(team){
  const delta = team.delta || '—';
  const deltaClass = delta.startsWith('+') ? 'positive' : delta.startsWith('-') ? 'negative' : 'neutral';
  const deltaIcon = delta.startsWith('+') ? '▲' : delta.startsWith('-') ? '▼' : '•';
  
  return `
    <div class="power-row">
      <span class="rank">${team.rank}</span>
      <span class="team-id">${team.team_id}</span>
      <span class="power-value">${team.power}</span>
      <span class="delta ${deltaClass}">
        <span class="delta-icon">${deltaIcon}</span>
        <span class="delta-text">${delta}</span>
      </span>
    </div>
  `;
}

function showErrorBanner(){
  const cardBody = CARD.querySelector('.card-body');
  if (cardBody && !cardBody.querySelector('.error-banner')) {
    const banner = document.createElement('div');
    banner.className = 'error-banner';
    banner.innerHTML = 'Couldn\'t load. Showing demo data.';
    cardBody.insertBefore(banner, cardBody.firstChild);
  }
}

// Auto-init when present
if (CARD) { initPowerRankings(); }
