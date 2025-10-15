// Team Schedule widget with native vertical scrollbar and one-line rows
// Format: Week X vs/at OPP (w-l) — SCORE [W/L]

const SCROLL = document.getElementById('schedule-scroll');
const LIST = document.getElementById('sched-list');
const DEMO = document.getElementById('sched-demo');

export async function initSchedule(){
  try{
    DEMO.hidden = true;
    const r = await fetch('/api/schedule', {headers:{'Accept':'application/json'}});
    if(!r.ok) throw new Error('status '+r.status);
    const data = await r.json();
    renderSchedule(data);
  }catch(_){
    DEMO.hidden = false;
    const data = demoSchedule();
    renderSchedule(data);
  }
}

function renderSchedule(data){
  const games = Array.isArray(data?.games) ? data.games : [];
  LIST.innerHTML = games.map(gameRow).join('');
}

function gameRow(g){
  const week = g.week || g.wk || '?';
  const opp = g.opponent || g.opp || '???';
  const home = g.home_team || g.home;
  const away = g.away_team || g.away;
  const isHome = home === 'NE' || home === 'New England Patriots' || g.home;
  const vsAt = isHome ? 'vs' : 'at';
  
  const oppRecord = g.opp_record || '8-9';
  const score = g.score || '—';
  const result = g.result || g.res || '—';
  
  const resultClass = result === 'W' ? 'W' : result === 'L' ? 'L' : '';
  
  return `<div class="sched-row">
    <div class="sched-left">
      <span class="sched-week">Week ${week}</span>
      <span class="sched-vs">${vsAt} ${opp}</span>
      <span class="sched-record">(${oppRecord})</span>
    </div>
    <div class="sched-right">
      <span class="sched-score">${score}</span>
      <span class="pill ${resultClass}">${result}</span>
    </div>
  </div>`;
}

function demoSchedule(){
  return {
    games: [
      {week:1, opp:'BUF', home:true, opp_record:'8-9', score:'24–21', result:'W'},
      {week:2, opp:'MIA', home:false, opp_record:'7-10', score:'17–28', result:'L'},
      {week:3, opp:'NYJ', home:true, opp_record:'6-11', score:'31–14', result:'W'},
      {week:4, opp:'BAL', home:false, opp_record:'11-6', score:'20–27', result:'L'},
      {week:5, opp:'CIN', home:true, opp_record:'9-8', score:'35–21', result:'W'},
      {week:6, opp:'LV', home:false, opp_record:'8-9', score:'24–17', result:'W'},
      {week:7, opp:'DEN', home:true, opp_record:'7-10', score:'28–14', result:'W'},
      {week:8, opp:'LAC', home:false, opp_record:'10-7', score:'21–31', result:'L'},
      {week:9, opp:'KC', home:true, opp_record:'12-5', score:'17–24', result:'L'},
      {week:10, opp:'TEN', home:false, opp_record:'6-11', score:'27–20', result:'W'},
      {week:11, opp:'HOU', home:true, opp_record:'9-8', score:'31–28', result:'W'},
      {week:12, opp:'IND', home:false, opp_record:'8-9', score:'24–21', result:'W'},
      {week:13, opp:'JAX', home:true, opp_record:'7-10', score:'28–17', result:'W'},
      {week:14, opp:'PIT', home:false, opp_record:'9-8', score:'21–24', result:'L'},
      {week:15, opp:'CLE', home:true, opp_record:'8-9', score:'27–20', result:'W'},
      {week:16, opp:'GB', home:false, opp_record:'10-7', score:'24–31', result:'L'},
      {week:17, opp:'DET', home:true, opp_record:'11-6', score:'28–21', result:'W'},
      {week:18, opp:'NYJ', home:false, opp_record:'6-11', score:'35–14', result:'W'}
    ]
  };
}

// Auto-init when present
if (SCROLL && LIST) { initSchedule(); }