// PlayByPlayBox component for vanilla JavaScript
// Frontend framework: Vanilla HTML/JavaScript

class PlayByPlayBox {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.pollMs = options.pollMs || 1000;
        this.plays = [];
        this.isAutoScroll = true;
        this.stableCount = 0;
        this.loading = true;
        this.error = null;
        this.prevLen = -1;
        this.stopped = false;
        this.intervalId = null;
        
        this.init();
    }
    
    init() {
        this.render();
        this.startPolling();
    }
    
    async fetchLastGame() {
        try {
            const response = await fetch(`${window.API_BASE}/last-game`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            const newPlays = data?.result?.plays ?? data?.plays ?? [];
            const newLen = newPlays.length;
            
            // Only update if there are actually new plays
            if (newLen > this.plays.length) {
                this.plays = newPlays;
                this.loading = false;
                this.error = null;
                
                this.render();
                
                // Only auto-scroll if user is near the bottom AND we have new plays
                if (this.isAutoScroll) {
                    this.scrollToBottom();
                }
            }
            
            if (this.prevLen >= 0 && newLen === this.prevLen) {
                this.stableCount++;
            } else {
                this.stableCount = 0;
            }
            this.prevLen = newLen;
            
            // Stop polling after 5 stable checks (instead of 3) to reduce server load
            if (this.stableCount >= 5) {
                this.stopPolling();
            }
            
        } catch (e) {
            this.error = e?.message || "Failed to load last game";
            this.loading = false;
            this.render();
        }
    }
    
    startPolling() {
        // Initial fetch
        this.fetchLastGame();
        
        // Set up polling
        this.intervalId = setInterval(() => {
            if (this.stopped) return;
            this.fetchLastGame();
        }, this.pollMs);
    }
    
    stopPolling() {
        this.stopped = true;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }
    
    scrollToBottom() {
        const scrollContainer = document.getElementById(`${this.containerId}-scroll`);
        if (scrollContainer) {
            scrollContainer.scrollTop = scrollContainer.scrollHeight;
        }
    }
    
    onScroll() {
        const scrollContainer = document.getElementById(`${this.containerId}-scroll`);
        if (!scrollContainer) return;
        
        const distanceFromBottom = scrollContainer.scrollHeight - scrollContainer.scrollTop - scrollContainer.clientHeight;
        // Use a much larger threshold to prevent jumping when user scrolls up
        // Only disable autoscroll if user has scrolled significantly up
        if (distanceFromBottom > 200) {
            this.isAutoScroll = false;
        } else {
            this.isAutoScroll = true;
        }
    }
    
    render() {
        const container = document.getElementById(this.containerId);
        if (!container) return;
        
        const playLines = this.plays.length === 0 && !this.loading 
            ? '<div class="text-neutral-400">No plays yet. Run a sim to populate play-by-play.</div>'
            : this.plays.map((p, i) => 
                `<li class="whitespace-pre-wrap" style="margin: 2px 0; padding: 1px 0;">[Q${p.quarter} ${p.clock}] ${p.down}&${p.distance} @ ${p.yardline} — ${p.desc}</li>`
            ).join('');
        
        container.innerHTML = `
            <div class="w-full">
                <div class="flex items-center justify-between mb-2">
                    <h3 class="text-base font-semibold text-neutral-200">Play-by-Play (Last Game)</h3>
                    <div class="text-xs text-neutral-400">
                        ${this.loading ? "Loading…" : `${this.plays.length} plays`}
                        ${this.error ? `<span class="text-red-400 ml-2">${this.error}</span>` : ''}
                    </div>
                </div>
                <div
                    id="${this.containerId}-scroll"
                    class="font-mono text-sm leading-6 h-[240px] overflow-y-auto bg-neutral-950 text-neutral-200 rounded-2xl border border-neutral-800 p-3"
                    style="font-family: 'Courier New', monospace; font-size: 14px; line-height: 24px; height: 240px; overflow-y: auto; background: #0a0a0a; color: #e5e5e5; border-radius: 16px; border: 1px solid #262626; padding: 12px;"
                >
                    ${this.plays.length === 0 && !this.loading ? 
                        '<div style="color: #a3a3a3;">No plays yet. Run a sim to populate play-by-play.</div>' : 
                        `<ul style="list-style: none; padding: 0; margin: 0;">
                            ${this.plays.map((p, i) => 
                                `<li style="white-space: pre-wrap; margin: 2px 0; padding: 1px 0; border-bottom: 1px solid #333;">[Q${p.quarter} ${p.clock}] ${p.down}&${p.distance} @ ${p.yardline} — ${p.desc}</li>`
                            ).join('')}
                        </ul>`
                    }
                </div>
            </div>
        `;
        
        // Attach scroll event listener
        const scrollContainer = document.getElementById(`${this.containerId}-scroll`);
        if (scrollContainer) {
            scrollContainer.addEventListener('scroll', () => this.onScroll());
        }
    }
    
    destroy() {
        this.stopPolling();
    }
}

// Export for use in other scripts
window.PlayByPlayBox = PlayByPlayBox;
