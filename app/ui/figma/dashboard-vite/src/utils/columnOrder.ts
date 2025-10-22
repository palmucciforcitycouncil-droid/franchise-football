export type ViewKey = "attributes"|"stats";

export function getSavedOrder(view: ViewKey): string[] | null {
  try { 
    return JSON.parse(localStorage.getItem(`roster.columns.${view}`) || "null"); 
  }
  catch { 
    return null; 
  }
}

export function saveOrder(view: ViewKey, keys: string[]) {
  try { 
    localStorage.setItem(`roster.columns.${view}`, JSON.stringify(keys)); 
  } catch {}
}

export function applyOrder<T extends {key: string}>(defs: T[], keys: string[]): T[] {
  const map = new Map(defs.map(d => [d.key, d]));
  const ordered: T[] = [];
  keys.forEach(k => { 
    const d = map.get(k); 
    if (d) { 
      ordered.push(d); 
      map.delete(k); 
    } 
  });
  // append any new/unknown columns at the end (forward compatible)
  map.forEach(d => ordered.push(d));
  return ordered;
}

export function defaultKeys<T extends {key: string}>(defs: T[]): string[] {
  return defs.map(d => d.key);
}

export function findGroupRange(columns: {key: string, group?: string}[], targetIndex: number): {start: number, end: number} | null {
  const targetColumn = columns[targetIndex];
  if (!targetColumn.group) return null;
  
  let start = targetIndex;
  let end = targetIndex;
  
  // Find start of group
  while (start > 0 && columns[start - 1].group === targetColumn.group) {
    start--;
  }
  
  // Find end of group
  while (end < columns.length - 1 && columns[end + 1].group === targetColumn.group) {
    end++;
  }
  
  return { start, end };
}

export function moveGroup(columns: {key: string, group?: string}[], fromIndex: number, toIndex: number): {key: string, group?: string}[] {
  const groupRange = findGroupRange(columns, fromIndex);
  if (!groupRange) {
    // Single column move
    const result = [...columns];
    const [moved] = result.splice(fromIndex, 1);
    result.splice(toIndex, 0, moved);
    return result;
  }
  
  // Move entire group
  const result = [...columns];
  const groupItems = result.splice(groupRange.start, groupRange.end - groupRange.start + 1);
  
  // Adjust target index if it was after the removed group
  const adjustedToIndex = toIndex > groupRange.end ? toIndex - (groupRange.end - groupRange.start + 1) : toIndex;
  
  result.splice(adjustedToIndex, 0, ...groupItems);
  return result;
}
