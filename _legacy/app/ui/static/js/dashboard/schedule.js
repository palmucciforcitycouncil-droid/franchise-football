// Team Schedule widget with native vertical scrollbar and one-line rows
// Format: Week X vs/at OPP (w-l) — SCORE [W/L]

import { demoSchedule, withDemo } from './demoData.js';

const SCROLL = document.getElementById('schedule-scroll');
const LIST = document.getElementById('sched-list');
const DEMO = document.getElementById('sched-demo');

export async function initSchedule(){
  const { data, isDemo } = await withDemo(
    async (signal) => {
      const r = await fetch('/api/schedule', {
        headers: {'Accept': 'application/json'},
        signal
      });
      if (!r.ok) throw new Error('status ' + r.status);
      return r.json();
    },
    demoSchedule
  );
  
  if (isDemo) {
    showErrorBanner();
    DEMO.hidden = false;
  } else {
    DEMO.hidden = true;
  }
  
  renderSchedule(data);
}

function renderSchedule(data){
  const games = Array.isArray(data) ? data : Array.isArray(data?.games) ? data.games : [];
  LIST.innerHTML = games.map(gameRow).join('');
}

function gameRow(g){
  const week = g.week || '?';
  const opp = g.opp || '???';
  const isHome = g.home;
  const vsAt = isHome ? 'vs' : 'at';
  
  const score = `${g.score_team || 0}–${g.score_opp || 0}`;
  const result = g.result || '—';
  const record = g.record || '8-9';
  
  const resultClass = result === 'W' ? 'W' : result === 'L' ? 'L' : '';
  
  return `<div class="sched-row">
    <div class="sched-left">
      <span class="sched-week">Week ${week}</span>
      <span class="sched-vs">${vsAt} ${opp}</span>
      <span class="sched-record">(${record})</span>
    </div>
    <div class="sched-right">
      <span class="sched-score">${score}</span>
      <span class="pill ${resultClass}" style="min-width:64px;text-align:center;">${result}</span>
    </div>
  </div>`;
}

function showErrorBanner(){
  const cardBody = document.querySelector('#schedule-card .card-body');
  if (cardBody && !cardBody.querySelector('.error-banner')) {
    const banner = document.createElement('div');
    banner.className = 'error-banner';
    banner.innerHTML = 'Couldn\'t load. Showing demo data.';
    cardBody.insertBefore(banner, cardBody.firstChild);
  }
}

// Auto-init when present
if (SCROLL && LIST) { initSchedule(); }