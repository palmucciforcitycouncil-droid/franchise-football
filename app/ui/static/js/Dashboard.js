// Dashboard.js - Main dashboard functionality
console.log('Dashboard.js loaded');

// Global dashboard state
let dashboardState = {
    currentWeek: 1,
    currentPhase: 'REGULAR_SEASON',
    selectedTeamId: 1,
    currentGameId: null,
    panels: {
        header: null,
        standings: null,
        powerRankings: null,
        leagueTopPerformers: null,
        box: null,
        pbp: null,
        schedule: null,
        scouting: null,
        teamTopPerformers: null
    },
    refresh: function() {
        console.log('Refreshing dashboard...');
        // Refresh all panels
        if (this.panels.header) {
            // Header doesn't need refresh
        }
        if (this.panels.standings) {
            this.panels.standings.load();
        }
        if (this.panels.powerRankings) {
            this.panels.powerRankings.load();
        }
        if (this.panels.leagueTopPerformers) {
            this.panels.leagueTopPerformers.load();
        }
        if (this.panels.box && this.currentGameId) {
            this.panels.box.load(this.currentGameId);
        }
        if (this.panels.pbp && this.currentGameId) {
            this.panels.pbp.load(this.currentGameId);
        }
        if (this.panels.schedule) {
            this.panels.schedule.load(this.selectedTeamId);
        }
        if (this.panels.scouting) {
            this.panels.scouting.load(this.getNextOpponentId());
        }
        if (this.panels.teamTopPerformers) {
            this.panels.teamTopPerformers.load(this.selectedTeamId);
        }
    },
    
    getNextOpponentId: function() {
        // Mock implementation - in real app, this would come from schedule data
        // For now, return a default opponent ID
        return 2; // Buffalo Bills
    }
};

// Check if current route is dashboard/home
function isDashboardRoute(){
    const p = location.pathname.toLowerCase();
    const h = (location.hash||'').toLowerCase();
    return p === '/' || p.includes('/dashboard') || h.includes('home') || h.includes('dashboard');
}

// Dashboard initialization
function initDashboard() {
    if (!isDashboardRoute()) return; // only init on dashboard/home
    console.log('Initializing dashboard...');
    console.log('Available window objects:', Object.keys(window).filter(k => k.includes('Scouting') || k.includes('TeamPerformance') || k.includes('GameLeaders')));
    
    try {
        // Check for required mount points
        const requiredElements = [
            'standings-side',
            'pbp-panel', 
            'box-panel',
            'team-schedule-panel',
            'scouting-box',
            'sim-week-button'
        ];
        
        const missingElements = [];
        requiredElements.forEach(id => {
            const element = document.querySelector(`[data-testid="${id}"]`);
            if (!element) {
                missingElements.push(id);
            } else {
                console.log(`Found element: ${id}`, element);
            }
        });
        
        // Also check for the scouting box content container
        const scoutingContainer = document.getElementById('scouting-box-content');
        console.log('Scouting box container found:', scoutingContainer);
        
        if (missingElements.length > 0) {
            console.error('Missing required elements:', missingElements);
            showDashboardError(`Missing required elements: ${missingElements.join(', ')}`);
            return;
        }
        
        // Initialize panels
        initializePanels();
        
        // Setup event handlers
        setupEventHandlers();
        
        // Load initial data
        loadInitialData();
        
        console.log('Dashboard initialized successfully');
        
    } catch (error) {
        console.error('Dashboard initialization failed:', error);
        showDashboardError(`Initialization failed: ${error.message}`);
    }
}

/**
 * Initialize all dashboard panels
 */
function initializePanels() {
    // Initialize header panel
    if (window.DashboardHeader) {
        dashboardState.panels.header = new window.DashboardHeader();
        dashboardState.panels.header.render();
    }
    
    // Initialize demo toggle
    if (window.DemoToggle) {
        window.demoToggle = new window.DemoToggle();
    }
    
    // Initialize standings panel
    if (window.StandingsPanel) {
        dashboardState.panels.standings = new window.StandingsPanel();
    }
    
    // Initialize power rankings panel
    if (window.PowerRankingsPanel) {
        dashboardState.panels.powerRankings = new window.PowerRankingsPanel();
    }
    
    // Initialize league top performers panel
    if (window.LeagueTopPerformersPanel) {
        dashboardState.panels.leagueTopPerformers = new window.LeagueTopPerformersPanel();
    }
    
    // Initialize box panel
    if (window.BoxPanel) {
        dashboardState.panels.box = new window.BoxPanel();
    }
    
    // Initialize PBP panel
    if (window.PBPClient) {
        dashboardState.panels.pbp = new window.PBPClient();
    }
    
    // Initialize team schedule panel
    if (window.TeamSchedulePanel) {
        dashboardState.panels.schedule = new window.TeamSchedulePanel();
    }
    
    // Initialize team top performers panel
    if (window.TeamTopPerformersPanel) {
        dashboardState.panels.teamTopPerformers = new window.TeamTopPerformersPanel();
    }
    
    // Initialize scouting box
    if (window.ScoutingBox) {
        console.log('Initializing ScoutingBox...');
        dashboardState.panels.scouting = new window.ScoutingBox();
        console.log('ScoutingBox initialized:', dashboardState.panels.scouting);
    } else {
        console.error('ScoutingBox class not found in window object');
    }
}

/**
 * Setup event handlers
 */
function setupEventHandlers() {
    // Sim Week button
    const simWeekBtn = document.getElementById('sim-week-button');
    if (simWeekBtn) {
        simWeekBtn.addEventListener('click', handleSimWeek);
    }
}

/**
 * Load initial dashboard data
 */
async function loadInitialData() {
    try {
        console.log('Starting to load initial dashboard data...');
        
        // Load season state
        console.log('Loading season state...');
        await loadSeasonState();
        
        // Load standings
        console.log('Loading standings...');
        await loadStandings();
        
        // Load power rankings
        console.log('Loading power rankings...');
        await loadPowerRankings();
        
        // Load league top performers
        console.log('Loading league top performers...');
        await loadLeagueTopPerformers();
        
        // Load team schedule
        console.log('Loading team schedule...');
        await loadTeamSchedule();
        
        // Load scouting box
        console.log('Loading scouting box...');
        await loadScoutingBox();
        
        // Load team top performers
        console.log('Loading team top performers...');
        await loadTeamTopPerformers();
        
        // Load latest game
        console.log('Loading latest game...');
        await loadLatestGame();
        
        // Load PBP for latest game
        console.log('Loading PBP...');
        await loadPBP();
        
        console.log('All initial data loaded successfully');
    } catch (error) {
        console.error('Failed to load initial data:', error);
    }
}

/**
 * Load scouting box
 */
async function loadScoutingBox() {
    try {
        console.log('Loading scouting box...');
        if (dashboardState.panels.scouting) {
            const nextOpponentId = dashboardState.getNextOpponentId();
            console.log('Loading scouting for opponent ID:', nextOpponentId);
            await dashboardState.panels.scouting.load(nextOpponentId);
            console.log('Scouting box loaded successfully');
            } else {
            console.error('Scouting panel not initialized');
        }
    } catch (error) {
        console.error('Failed to load scouting box:', error);
    }
}

/**
 * Load season state
 */
async function loadSeasonState() {
    try {
        const response = await fetch(buildUrl('/season'));
        if (response.ok) {
            const data = await response.json();
            dashboardState.currentWeek = data.week || 1;
            dashboardState.currentPhase = data.phase || 'REGULAR_SEASON';
            
            // Update week label
            updateWeekLabel(dashboardState.currentWeek);
        }
    } catch (error) {
        console.error('Failed to load season state:', error);
    }
}

/**
 * Load standings
 */
async function loadStandings() {
    if (dashboardState.panels.standings) {
        try {
            await dashboardState.panels.standings.load();
        } catch (error) {
            console.error('Failed to load standings:', error);
        }
    }
}

/**
 * Load team schedule
 */
async function loadTeamSchedule() {
    if (dashboardState.panels.schedule) {
        try {
            await dashboardState.panels.schedule.load(dashboardState.selectedTeamId);
        } catch (error) {
            console.error('Failed to load team schedule:', error);
        }
    }
}

/**
 * Load top performers
 */
async function loadTopPerformers() {
    if (dashboardState.panels.topPerformers) {
        try {
            await dashboardState.panels.topPerformers.load();
        } catch (error) {
            console.error('Failed to load top performers:', error);
        }
    }
}

/**
 * Load latest game
 */
async function loadLatestGame() {
    if (dashboardState.panels.box) {
        try {
            const response = await fetch(buildUrl('/games/latest'));
            if (response.ok) {
                const data = await response.json();
                dashboardState.currentGameId = data.game_id || data.id;
                await dashboardState.panels.box.load(dashboardState.currentGameId);
            } else {
                // Fallback to mock data when API is not available
                console.log('Latest game API not available, using mock data');
                dashboardState.currentGameId = 'mock-game-1';
                await dashboardState.panels.box.load(dashboardState.currentGameId);
            }
        } catch (error) {
            console.error('Failed to load latest game, using mock data:', error);
            // Fallback to mock data
            dashboardState.currentGameId = 'mock-game-1';
            await dashboardState.panels.box.load(dashboardState.currentGameId);
        }
    }
}

/**
 * Load PBP for latest game
 */
async function loadPBP() {
    if (dashboardState.panels.pbp) {
        try {
            // Use currentGameId if available, otherwise use mock game ID
            const gameId = dashboardState.currentGameId || 'mock-game-1';
            console.log('Loading PBP for game:', gameId);
            await dashboardState.panels.pbp.load(gameId);
        } catch (error) {
            console.error('Failed to load PBP:', error);
        }
    }
}

/**
 * Handle Sim Week button click
 */
async function handleSimWeek() {
    const simBtn = document.getElementById('sim-week-button');
    if (!simBtn) return;
    
    try {
        // Disable button
        simBtn.disabled = true;
        simBtn.textContent = 'Simulating...';
        
        // Call sim week endpoint
        const response = await fetch(buildUrl('/season/sim-week'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('Week simulation complete:', result);
            
            // Handle game results
            if (result.game_results && result.game_results.length > 0) {
                // Find user team's game
                const userGame = result.game_results.find(game => 
                    game.home_team_id === dashboardState.selectedTeamId || 
                    game.away_team_id === dashboardState.selectedTeamId
                ) || result.game_results[0];
                
                dashboardState.currentGameId = userGame.game_id;
                
                // Refresh all panels
                await Promise.all([
                    refreshBoxPanel(),
                    refreshPBPPanel(),
                    refreshStandings(),
                    refreshTeamSchedule(),
                    refreshTopPerformers()
                ]);
                
                // Update week
                if (result.week) {
                    dashboardState.currentWeek = result.week;
                    updateWeekLabel(result.week);
                }
            }
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
    } catch (error) {
        console.error('Sim week failed:', error);
        alert(`Simulation failed: ${error.message}`);
    } finally {
        // Re-enable button
        simBtn.disabled = false;
        simBtn.textContent = 'Sim Week';
    }
}

/**
 * Refresh box panel
 */
async function refreshBoxPanel() {
    if (dashboardState.panels.box && dashboardState.currentGameId) {
        await dashboardState.panels.box.load(dashboardState.currentGameId);
    }
}

/**
 * Refresh PBP panel
 */
async function refreshPBPPanel() {
    if (dashboardState.panels.pbp && dashboardState.currentGameId) {
        await dashboardState.panels.pbp.load(dashboardState.currentGameId);
    }
}

/**
 * Refresh standings
 */
async function refreshStandings() {
    if (dashboardState.panels.standings) {
        await dashboardState.panels.standings.load();
    }
}

/**
 * Refresh team schedule
 */
async function refreshTeamSchedule() {
    if (dashboardState.panels.schedule) {
        await dashboardState.panels.schedule.load(dashboardState.selectedTeamId);
    }
}

/**
 * Refresh top performers
 */
async function refreshTopPerformers() {
    if (dashboardState.panels.topPerformers) {
        await dashboardState.panels.topPerformers.load();
    }
}

/**
 * Load power rankings
 */
async function loadPowerRankings() {
    try {
        console.log('Loading power rankings...');
        if (dashboardState.panels.powerRankings) {
            await dashboardState.panels.powerRankings.load();
            console.log('Power rankings loaded successfully');
        } else {
            console.error('Power rankings panel not initialized');
        }
    } catch (error) {
        console.error('Failed to load power rankings:', error);
    }
}

/**
 * Load league top performers
 */
async function loadLeagueTopPerformers() {
    try {
        console.log('Loading league top performers...');
        if (dashboardState.panels.leagueTopPerformers) {
            await dashboardState.panels.leagueTopPerformers.load();
            console.log('League top performers loaded successfully');
        } else {
            console.error('League top performers panel not initialized');
        }
    } catch (error) {
        console.error('Failed to load league top performers:', error);
    }
}

/**
 * Load team top performers
 */
async function loadTeamTopPerformers() {
    try {
        console.log('Loading team top performers...');
        if (dashboardState.panels.teamTopPerformers) {
            await dashboardState.panels.teamTopPerformers.load(dashboardState.selectedTeamId);
            console.log('Team top performers loaded successfully');
        } else {
            console.error('Team top performers panel not initialized');
        }
    } catch (error) {
        console.error('Failed to load team top performers:', error);
    }
}

/**
 * Update week label
 */
function updateWeekLabel(week) {
    const weekLabel = document.getElementById('week-label');
    if (weekLabel) {
        weekLabel.textContent = `Week ${week}`;
    }
}

/**
 * Show dashboard error
 */
function showDashboardError(message) {
    const mainContent = document.getElementById('main-content');
    if (mainContent) {
        mainContent.innerHTML = `
            <div class="p-6">
                <h1 class="text-2xl font-bold text-white mb-4">Dashboard Error</h1>
                <div class="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded">
                    <p class="font-bold">Dashboard Error</p>
                    <p>${message}</p>
                </div>
            </div>
        `;
    }
}

// Make initDashboard and dashboardState available globally
window.initDashboard = initDashboard;
window.dashboardState = dashboardState;

// Export for module usage if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { initDashboard };
}