// app/ui/static/gm_hooks.js
window.GM = {
  async loadExpiring(teamId, season){
    const r = await fetch(`/api/v1/gm/expiring?team_id=${teamId}&season=${season}`);
    return await r.json(); // [{player_id,...}]
  },
  async negotiate(playerId, teamId, season, years, total){
    const r = await fetch(`/api/v1/gm/negotiate/${playerId}?team_id=${teamId}`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({season, years, total})
    });
    return await r.json(); // {accepted,min_years,min_total}
  },
  async release(playerId){
    const r = await fetch(`/api/v1/gm/release/${playerId}`, {method:"POST"});
    return await r.json();
  },
  async tradeQuote(playerId, season){
    const r = await fetch(`/api/v1/gm/trade/quote/${playerId}?season=${season}`);
    return await r.json(); // {ask_value_units, discounted}
  },
  async preseasonSweep(season){
    const r = await fetch(`/api/v1/gm/preseason/expiring_ai_sweep?season=${season}`, {method:"POST"});
    return await r.json();
  }
};


