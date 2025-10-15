/* dashboard-wire v1.0 — no template edits required */
(function(){
  const LOG='[dashboard-wire]';
  console.info(LOG,'boot');

  const T = {
    season: /season status/i,
    champs: /championship/i,
    leaders:/leaders/i,
    btnSim: /simulate week/i,
    btnPO:  /start playoffs/i,
    btnOS:  /process offseason/i,
  };

  function findCard(regex){
    // look for a heading then return its nearest card/panel container
    const hs=[...document.querySelectorAll('h1,h2,h3,h4,strong,header,div')];
    const h = hs.find(el => regex.test(el.textContent||''));
    if(!h) return null;
    // walk up to something that looks like a card/panel
    let n=h; for(let i=0;i<5 && n; i++, n=n.parentElement){
      if(n.classList && /card|panel|box|container|section|tile/i.test(n.className)) return n;
    }
    return h.closest('section,div') || h.parentElement;
  }

  function ensureField(card, label, dataKey){
    if(!card) return null;
    let slot = card.querySelector(`[data-field="${dataKey}"]`);
    if(!slot){
      // append a simple row quietly if the template had plain text before
      slot = document.createElement('span');
      slot.setAttribute('data-field', dataKey);
      slot.style.whiteSpace='pre-wrap';
      // try to place into a body-ish element
      (card.querySelector('.card-body, .panel, .content, .body') || card).appendChild(slot);
    }
    return slot;
  }

  function findButton(regex){
    const btns=[...document.querySelectorAll('button,a,input[type="button"],input[type="submit"]')];
    return btns.find(b => regex.test((b.textContent||b.value||'').trim()));
  }

  async function render(){
    const api = window.uiAdapters?.dashboard;
    if(!api){ console.error(LOG,'adapter missing'); return; }

    const seasonCard = findCard(T.season);
    const champsCard = findCard(T.champs);
    const leadersCard= findCard(T.leaders);

    const [season, champs, leaders] = await Promise.all([
      api.getSeasonSummary(), api.getChampionship(), api.getLeaders()
    ]);

    // season fields
    const fWeek   = ensureField(seasonCard,'Week','week');
    const fRecord = ensureField(seasonCard,'Record','record');
    const fHealth = ensureField(seasonCard,'Health','health');
    if(fWeek)   fWeek.textContent   = `Week ${season?.week ?? '?'}`;
    if(fRecord) fRecord.textContent = `  •  ${season?.record ?? ''}`;
    if(fHealth) fHealth.textContent = `  •  ${season?.health ?? ''}`;

    // champs
    const fChamp = ensureField(champsCard,'Champion','champion');
    if(fChamp) {
      fChamp.textContent = champs?.champion
        ? `Champion: ${champs.champion}`
        : (champs?.stage ? `(${champs.stage})` : 'No champion yet.');
    }

    // leaders
    const fLead = ensureField(leadersCard,'Leaders','leaders');
    if(fLead){
      const qb = leaders?.qb, rb = leaders?.rb;
      fLead.textContent = [
        qb ? `QB: ${qb.name} (OVR ${qb.ovr})` : null,
        rb ? `RB: ${rb.name} (OVR ${rb.ovr})` : null
      ].filter(Boolean).join('   |   ');
    }

    console.info(LOG,'rendered');
  }

  function wireButtons(){
    const api = window.uiAdapters?.dashboard;
    if(!api) return;

    const bSim = findButton(T.btnSim);
    const bPO  = findButton(T.btnPO);
    const bOS  = findButton(T.btnOS);

    if(bSim && !bSim.dataset.wired){
      bSim.dataset.wired='1';
      bSim.addEventListener('click', async (e)=>{ e.preventDefault(); console.info(LOG,'simulate'); await api.simulateWeek(); render(); });
    }
    if(bPO && !bPO.dataset.wired){
      bPO.dataset.wired='1';
      bPO.addEventListener('click', async (e)=>{ e.preventDefault(); console.info(LOG,'playoffs'); await api.startPlayoffs(); render(); });
    }
    if(bOS && !bOS.dataset.wired){
      bOS.dataset.wired='1';
      bOS.addEventListener('click', async (e)=>{ e.preventDefault(); console.info(LOG,'offseason'); await api.processOffseason(); render(); });
    }
  }

  function boot(){
    render(); wireButtons();
    // In case SPA swaps content after load, watch for changes and re-wire.
    const mo = new MutationObserver(()=>{ wireButtons(); });
    mo.observe(document.body, { childList:true, subtree:true });
  }

  if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded', boot); }
  else { boot(); }
})();
