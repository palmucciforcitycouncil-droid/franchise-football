/**
 * Playoffs Page JavaScript
 * Handles interactions and future score entry functionality
 */

(function() {
    'use strict';

    // Configuration
    const API_BASE = '/api/playoffs';

    /**
     * Initialize playoffs page
     */
    function initialize() {
        setupMatchCardInteractions();
        setupResponsiveHandling();
        console.log('Playoffs page initialized');
    }

    /**
     * Setup match card click interactions
     */
    function setupMatchCardInteractions() {
        const matchCards = document.querySelectorAll('.match-card:not(.placeholder)');
        
        matchCards.forEach(card => {
            card.addEventListener('click', handleMatchCardClick);
            
            // Add keyboard support
            card.setAttribute('tabindex', '0');
            card.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleMatchCardClick(e);
                }
            });
        });
    }

    /**
     * Handle match card click (future: open score entry modal)
     */
    function handleMatchCardClick(event) {
        const card = event.currentTarget;
        const gameId = card.dataset.gameId;
        
        if (!gameId) {
            console.log('No game ID found for match card');
            return;
        }

        // For now, just show a simple alert
        // In the future, this would open a score entry modal
        const awayTeam = card.querySelector('.away-team').textContent;
        const homeTeam = card.querySelector('.home-team').textContent;
        
        console.log(`Match card clicked: ${awayTeam} @ ${homeTeam} (Game ID: ${gameId})`);
        
        // Show temporary feedback
        showMatchCardFeedback(card);
        
        // TODO: Open score entry modal
        // openScoreEntryModal(gameId, awayTeam, homeTeam);
    }

    /**
     * Show visual feedback when match card is clicked
     */
    function showMatchCardFeedback(card) {
        card.classList.add('loading');
        
        setTimeout(() => {
            card.classList.remove('loading');
            
            // Add a subtle highlight effect
            card.style.borderColor = '#d4af37';
            card.style.backgroundColor = 'rgba(212, 175, 55, 0.1)';
            
            setTimeout(() => {
                card.style.borderColor = '';
                card.style.backgroundColor = '';
            }, 1000);
        }, 500);
    }

    /**
     * Setup responsive handling
     */
    function setupResponsiveHandling() {
        const bracketGrid = document.querySelector('.bracket-grid');
        const huntSidebar = document.querySelector('.hunt-sidebar');
        
        if (!bracketGrid || !huntSidebar) return;

        // Handle window resize
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(handleResize, 250);
        });

        // Initial call
        handleResize();
    }

    /**
     * Handle responsive layout changes
     */
    function handleResize() {
        const isMobile = window.innerWidth <= 960;
        const bracketGrid = document.querySelector('.bracket-grid');
        const huntSidebar = document.querySelector('.hunt-sidebar');
        
        if (!bracketGrid || !huntSidebar) return;

        if (isMobile) {
            // Mobile: Stack vertically and move hunt to bottom
            bracketGrid.style.gridTemplateColumns = '1fr';
            huntSidebar.style.order = '4';
        } else {
            // Desktop: Three column layout with hunt on right
            bracketGrid.style.gridTemplateColumns = '1fr auto 1fr';
            huntSidebar.style.order = 'initial';
        }
    }

    /**
     * Future: Open score entry modal
     */
    function openScoreEntryModal(gameId, awayTeam, homeTeam) {
        // This would create and show a modal for entering scores
        console.log('Score entry modal would open for:', gameId, awayTeam, homeTeam);
        
        // Example modal structure:
        /*
        const modal = document.createElement('div');
        modal.className = 'score-entry-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>Enter Score</h3>
                <div class="score-inputs">
                    <label>${awayTeam}: <input type="number" id="away-score"></label>
                    <label>${homeTeam}: <input type="number" id="home-score"></label>
                </div>
                <div class="modal-actions">
                    <button onclick="saveScore(${gameId})">Save</button>
                    <button onclick="closeModal()">Cancel</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        */
    }

    /**
     * Future: Save score and update bracket
     */
    async function saveScore(gameId, awayScore, homeScore) {
        try {
            const response = await fetch(`${API_BASE}/matchup/${gameId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    away_score: awayScore,
                    home_score: homeScore,
                    winner_team_id: awayScore > homeScore ? 'away' : 'home'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const updatedMatchup = await response.json();
            updateMatchCard(gameId, updatedMatchup);
            
        } catch (error) {
            console.error('Failed to save score:', error);
            showToast('Failed to save score', 'error');
        }
    }

    /**
     * Future: Update match card with new score
     */
    function updateMatchCard(gameId, matchup) {
        const card = document.querySelector(`[data-game-id="${gameId}"]`);
        if (!card) return;

        const awayScoreEl = card.querySelector('.away-team').nextElementSibling;
        const homeScoreEl = card.querySelector('.home-team').previousElementSibling;
        
        awayScoreEl.textContent = matchup.away_score;
        homeScoreEl.textContent = matchup.home_score;
        
        // Highlight winner
        const awayTeamEl = card.querySelector('.away-team');
        const homeTeamEl = card.querySelector('.home-team');
        
        if (matchup.away_score > matchup.home_score) {
            awayTeamEl.classList.add('winner');
            homeTeamEl.classList.remove('winner');
        } else {
            homeTeamEl.classList.add('winner');
            awayTeamEl.classList.remove('winner');
        }
    }

    /**
     * Show toast notification
     */
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        // Style the toast
        Object.assign(toast.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 16px',
            borderRadius: '6px',
            color: 'white',
            fontWeight: '500',
            zIndex: '1000',
            transition: 'all 0.3s ease'
        });

        // Set background color based on type
        switch (type) {
            case 'success':
                toast.style.backgroundColor = '#22c55e';
                break;
            case 'error':
                toast.style.backgroundColor = '#ef4444';
                break;
            case 'warning':
                toast.style.backgroundColor = '#f59e0b';
                break;
            default:
                toast.style.backgroundColor = '#3b82f6';
        }

        document.body.appendChild(toast);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }

    /**
     * Future: Refresh playoff data
     */
    async function refreshPlayoffData() {
        try {
            const response = await fetch(`${API_BASE}?season=2025`);
            const data = await response.json();
            
            // Update the page with new data
            updatePlayoffBracket(data);
            
        } catch (error) {
            console.error('Failed to refresh playoff data:', error);
            showToast('Failed to refresh data', 'error');
        }
    }

    /**
     * Future: Update playoff bracket with new data
     */
    function updatePlayoffBracket(playoffData) {
        // This would update the entire bracket with new data
        console.log('Updating playoff bracket with:', playoffData);
        
        // Implementation would involve:
        // 1. Update match scores
        // 2. Move winners to next round
        // 3. Update "In the Hunt" lists
        // 4. Highlight advancing teams
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

    // Expose functions globally for future use
    window.playoffsPage = {
        saveScore,
        refreshPlayoffData,
        showToast
    };

})();