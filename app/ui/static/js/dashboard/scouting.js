// Scouting — Next Opponent widget with Overview/Tendencies tabs
import { demoScout, withDemo } from './demoData.js';

const CARD = document.getElementById('scout-card');
const DEMO = document.getElementById('scout-demo');

export async function initScouting(){
  if (!CARD) return;
  
  const { data, isDemo } = await withDemo(
    async (signal) => {
      const r = await fetch('/api/scouting/next', {
        headers: {'Accept': 'application/json'},
        signal
      });
      if (!r.ok) throw new Error('status ' + r.status);
      return r.json();
    },
    demoScout
  );
  
  if (isDemo) {
    showErrorBanner();
    DEMO.hidden = false;
  } else {
    DEMO.hidden = true;
  }
  
  renderScouting(data);
}

function renderScouting(data){
  const cardBody = CARD.querySelector('.card-body');
  if (!cardBody) return;
  
  cardBody.innerHTML = `
    <div class="scout-tabs">
      <button class="tab-btn active" data-tab="overview">Overview</button>
      <button class="tab-btn" data-tab="tendencies">Tendencies</button>
    </div>
    <div class="tab-content">
      <div id="scout-overview" class="tab-pane active"></div>
      <div id="scout-tendencies" class="tab-pane"></div>
    </div>
  `;
  
  renderOverview(data);
  renderTendencies(data);
  wireTabs();
}

function renderOverview(data){
  const overview = document.getElementById('scout-overview');
  if (!overview) return;
  
  const leaders = data.leaders || {};
  const injuries = data.injuries || [];
  
  overview.innerHTML = `
    <div class="scout-overview">
      <div class="opp-header">
        <span class="opp-pill">${data.team_id || 'TBD'}</span>
        <span class="opp-record">${data.record || '—'}</span>
        <span class="opp-streak">${data.streak || '—'}</span>
      </div>
      
      <div class="last3-section">
        <div class="section-title">Last 3 Games</div>
        <div class="last3-chips">
          ${(data.last3 || []).map(game => `<span class="chip ${game.startsWith('W') ? 'W' : 'L'}">${game}</span>`).join('')}
        </div>
      </div>
      
      <div class="leaders-section">
        <div class="section-title">Key Players</div>
        <div class="leaders-list">
          ${Object.entries(leaders).map(([pos, player]) => 
            `<div class="leader-row"><span class="pos">${pos}:</span><span class="player">${player}</span></div>`
          ).join('')}
        </div>
      </div>
      
      ${injuries.length > 0 ? `
        <div class="injuries-section">
          <div class="section-title">Injuries</div>
          <div class="injuries-list">
            ${injuries.map(injury => `<span class="injury-tag">${injury}</span>`).join('')}
          </div>
        </div>
      ` : ''}
    </div>
  `;
}

function renderTendencies(data){
  const tendencies = document.getElementById('scout-tendencies');
  if (!tendencies) return;
  
  const t = data.tendencies || {};
  
  tendencies.innerHTML = `
    <div class="scout-tendencies">
      <div class="tendency-row">
        <label>Run %</label>
        <div class="mini-bar"><div class="bar-fill" style="width:${t.run || 0}%"></div></div>
        <span class="value">${t.run || 0}%</span>
      </div>
      
      <div class="tendency-row">
        <label>Pass %</label>
        <div class="mini-bar"><div class="bar-fill" style="width:${t.pass || 0}%"></div></div>
        <span class="value">${t.pass || 0}%</span>
      </div>
      
      <div class="tendency-row">
        <label>Pace</label>
        <div class="mini-bar"><div class="bar-fill" style="width:${t.pace || 0}%"></div></div>
        <span class="value">${t.pace || 0}</span>
      </div>
      
      <div class="tendency-row">
        <label>4th-Down Aggression</label>
        <div class="mini-bar"><div class="bar-fill" style="width:${t.aggression || 0}%"></div></div>
        <span class="value">${t.aggression || 0}%</span>
      </div>
      
      <div class="tendency-row">
        <label>Blitz %</label>
        <div class="mini-bar"><div class="bar-fill" style="width:${t.blitz || 0}%"></div></div>
        <span class="value">${t.blitz || 0}%</span>
      </div>
      
      <div class="tendency-row">
        <label>Man Coverage</label>
        <div class="mini-bar"><div class="bar-fill" style="width:${t.man || 0}%"></div></div>
        <span class="value">${t.man || 0}%</span>
      </div>
      
      <div class="tendency-row">
        <label>Zone Coverage</label>
        <div class="mini-bar"><div class="bar-fill" style="width:${t.zone || 0}%"></div></div>
        <span class="value">${t.zone || 0}%</span>
      </div>
    </div>
  `;
}

function wireTabs(){
  const tabBtns = CARD.querySelectorAll('.tab-btn');
  const tabPanes = CARD.querySelectorAll('.tab-pane');
  
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.dataset.tab;
      
      // Update active states
      tabBtns.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));
      
      btn.classList.add('active');
      document.getElementById(`scout-${targetTab}`).classList.add('active');
    });
  });
}

function showErrorBanner(){
  const cardBody = CARD.querySelector('.card-body');
  if (cardBody && !cardBody.querySelector('.error-banner')) {
    const banner = document.createElement('div');
    banner.className = 'error-banner';
    banner.innerHTML = 'Opponent TBD. Showing league-average demo profile.';
    cardBody.insertBefore(banner, cardBody.firstChild);
  }
}

// Auto-init when present
if (CARD) { initScouting(); }
