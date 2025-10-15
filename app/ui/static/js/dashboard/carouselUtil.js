// Simple pager/carousel helper with keyboard & button control.
export function makePager({getCount, setPage, getPage, leftBtn, rightBtn}) {
  function apply() {
    const n = getCount();
    const p = Math.max(0, Math.min(getPage(), n ? n - 1 : 0));
    leftBtn.disabled  = (p <= 0);
    rightBtn.disabled = (p >= n - 1);
  }
  
  leftBtn.addEventListener('click', () => { 
    setPage(getPage() - 1); 
    apply(); 
  });
  
  rightBtn.addEventListener('click', () => { 
    setPage(getPage() + 1); 
    apply(); 
  });
  
  // Keyboard support when header focused
  [leftBtn, rightBtn].forEach(btn=>{
    btn.addEventListener('keydown', (e)=>{
      if(e.key === 'ArrowLeft'){ leftBtn.click(); }
      if(e.key === 'ArrowRight'){ rightBtn.click(); }
    });
  });
  
  // public re-apply after data load
  return { apply };
}
