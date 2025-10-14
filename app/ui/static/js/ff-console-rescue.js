/* ff-console-rescue.js v1.0 — FF Roster Console Rescue
   Emergency script that can be pasted into browser console or loaded as external script.
   Force-mounts roster shell and renders fallback table immediately. */
(() => {
  const LOG='[ff-console-rescue]';
  
  function host(){
    return document.querySelector('#app-root')||
           document.querySelector('main')||
           document.querySelector('#content')||
           document.body;
  }
  
  function mountShell(){
    if(document.getElementById('page-roster')) return true;
    const h=host(); if(!h){ console.warn(LOG,'no host'); return false; }
    const el=document.createElement('section');
    el.id='page-roster'; 
    el.dataset.testid='page-roster'; 
    el.className='page roster-page';
    el.innerHTML=`
      <header class="mb-3"><h2 class="text-lg font-semibold">Roster</h2></header>
      <div class="grid grid-cols-12 gap-4">
        <section class="col-span-12">
          <div class="flex items-center gap-2 mb-2">
            <button id="btn-auto-assign" data-action="auto-assign" class="btn">Auto Assign</button>
            <button id="btn-undo-assign" data-action="undo-assign" class="btn btn-secondary">Undo</button>
          </div>
          <section id="roster-main" class="card panel min-h-[360px]" data-roster-root></section>
        </section>
        <section class="col-span-12">
          <h3 class="text-base font-semibold mb-2">Depth Chart</h3>
          <div class="grid grid-cols-12 gap-4">
            <section id="depth-offense"  class="col-span-12 card panel min-h-[220px]" data-depth-offense></section>
            <section id="depth-defense"  class="col-span-12 card panel min-h-[220px]" data-depth-defense></section>
            <section id="depth-special"  class="col-span-12 card panel min-h-[180px]" data-depth-special></section>
          </div>
        </section>
      </div>`;
    
    el.addEventListener('click',(e)=>{
      const a=e.target?.dataset?.action;
      if(a==='auto-assign') window.dispatchEvent(new CustomEvent('ff:depth:autoAssign'));
      if(a==='undo-assign')  window.dispatchEvent(new CustomEvent('ff:depth:undo'));
    });
    
    h.appendChild(el);
    window.dispatchEvent(new Event('ff:roster:rendered'));
    console.info(LOG,'shell mounted');
    return true;
  }
  
  async function getRoster(){
    try{
      if (typeof window.uiAdapters?.roster?.getTeamRoster==='function') return await window.uiAdapters.roster.getTeamRoster();
      if (window.FF?.data?.activeTeamRoster) return window.FF.data.activeTeamRoster;
      if (window.FF?.data?.demo?.roster) return window.FF.data.demo.roster;
    }catch(e){}
    return [
      { id:'qb_1', name:'Alex Carter', pos:'QB', ovr:74 },
      { id:'rb_1', name:'Miles Stone', pos:'RB', ovr:71 },
      { id:'wr_1', name:'Jay Banks',   pos:'WR', ovr:73 },
      { id:'te_1', name:'D. Clark',    pos:'TE', ovr:69 },
      { id:'k_1',  name:'K. Hale',     pos:'K',  ovr:68 },
    ];
  }
  
  async function renderTable(){
    const root=document.querySelector('#roster-main[data-roster-root]');
    if(!root){ console.warn(LOG,'no #roster-main'); return; }
    const roster=await getRoster();
    const rows=(roster||[]).map(p=>`<tr>
      <td class="sticky left-0 bg-base-200 px-2">${p.name || [p.first_name,p.last_name].filter(Boolean).join(' ')}</td>
      <td>${p.pos ?? ''}</td><td>${p.ovr ?? ''}</td>
    </tr>`).join('');
    root.innerHTML=`
      <div class="mb-2 text-sm opacity-70">Roster (Console Rescue)</div>
      <div class="overflow-auto border border-base-300 rounded">
        <table class="w-full min-w-[520px] text-sm">
          <thead><tr><th class="sticky left-0 bg-base-300 text-left px-2">Name</th><th>Pos</th><th>OVR</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
    console.info(LOG,`rendered ${roster?.length||0} players`);
  }
  
  // Auto-execute if on roster route
  function onRosterRoute(){
    const p=(location.pathname||'').toLowerCase();
    const h=(location.hash||'').toLowerCase();
    return p.endsWith('/roster') || h.includes('roster');
  }
  
  if (onRosterRoute()) {
    if (mountShell()) renderTable();
  }
  
  // Expose global function for manual execution
  window.ffConsoleRescue = () => {
    console.info(LOG,'Manual rescue triggered');
    if (mountShell()) renderTable();
  };
  
})();
