// API helper for /last-game endpoint
// Frontend framework: Vanilla HTML/JavaScript

export const PlayDTO = {
    quarter: Number,
    clock: String,
    down: Number,
    distance: Number,
    yardline: String,
    desc: String
};

export async function getLastGame(base = window.API_BASE || 'http://127.0.0.1:8000') {
    const url = base.replace(/\/$/, "") + "/last-game";
    const res = await fetch(url, { method: "GET" });
    if (!res.ok) throw new Error(`GET /last-game ${res.status}`);
    const data = await res.json();
    return { 
        plays: Array.isArray(data?.plays) ? data.plays : [], 
        ...data 
    };
}


