export async function j(url, opts={}) {
  const r = await fetch(url, {headers:{'Content-Type':'application/json'}, ...opts});
  if(!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  try { return await r.json(); } catch { return {}; }
}
export function qs(s,root=document){return root.querySelector(s)}
export function qsa(s,root=document){return [...root.querySelectorAll(s)]}
export function el(tag, props={}, ...kids){
  const n = document.createElement(tag);
  Object.assign(n, props);
  kids.flat().forEach(k=> n.append(k?.nodeType ? k : document.createTextNode(k)));
  return n;
}
