/**
 * Roster Page JavaScript with Depth Chart Dropdowns
 * Handles persistence, validation, and auto-fill functionality
 */

(async function(){
  // Configuration
  const teamId = window.__TEAM_ID__ || 'NE';
  const season = window.__SEASON__ || new Date().getFullYear();
  
  // DOM elements
  const depthBox = document.getElementById('depthChartContainer');
  const btnAuto = document.getElementById('btnAutoFillDepth');
  const warningsBar = document.getElementById('warningsBar');
  const warningsList = document.getElementById('warningsList');
  const rosterTableBody = document.getElementById('rosterTableBody');
  
  // State
  let rosterData = [];
  let depthChartData = null;
  let playerDropdowns = new Map(); // slot -> dropdown element

  /**
   * Initialize the roster page
   */
  async function initialize() {
    try {
      // Load roster data
      await loadRoster();
      
      // Load depth chart
      await loadDepthChart();
      
      // Render roster table
      renderRosterTable();
      
      // Render depth chart with dropdowns
      renderDepthChart();
      
      console.log(`Roster page initialized for team ${teamId}, season ${season}`);
    } catch (error) {
      console.error('Failed to initialize roster page:', error);
      showToast('Failed to load roster data', 'error');
    }
  }

  /**
   * Load team roster data
   */
  async function loadRoster() {
    try {
      const response = await fetch(`/api/teams/${teamId}/roster?season=${season}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      rosterData = data.players || [];
    } catch (error) {
      console.error('Failed to load roster:', error);
      // Fallback to mock data
      rosterData = getMockRoster();
    }
  }

  /**
   * Load depth chart data
   */
  async function loadDepthChart() {
    try {
      const response = await fetch(`/api/teams/${teamId}/depthchart?season=${season}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      depthChartData = await response.json();
    } catch (error) {
      console.error('Failed to load depth chart:', error);
      depthChartData = null;
    }
  }

  /**
   * Render roster table
   */
  function renderRosterTable() {
    if (!rosterTableBody) return;
    
    const html = rosterData.map(player => `
      <tr class="border-b border-[#2d4a6f]/50 hover:bg-[#2d4a6f]/30">
        <td class="p-3">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-[#2d4a6f] flex items-center justify-center text-white text-xs">
              ${player.number || '--'}
            </div>
            <div>
              <a href="/players/${player.id}" 
                 data-entity="player" 
                 data-id="${player.id}" 
                 class="entity-link text-white hover:text-[#d4af37]">
                ${player.name}
              </a>
              <div class="text-[#94a3b8] text-xs">${player.position} · Age ${player.age}</div>
            </div>
          </div>
        </td>
        <td class="text-right p-3">
          <span class="px-2 py-1 rounded bg-[#d4af37]/20 text-[#d4af37] border border-[#d4af37]/30">
            ${player.overall_rating || '--'}
          </span>
        </td>
        <td class="text-right p-3 text-white">${player.speed || '--'}</td>
        <td class="text-right p-3 text-white">${player.strength || '--'}</td>
        <td class="text-right p-3 text-white">${player.agility || '--'}</td>
        <td class="text-right p-3 text-white">${player.throw_power || '--'}</td>
        <td class="text-right p-3 text-white">${player.throw_accuracy || '--'}</td>
        <td class="text-right p-3 text-white">${player.catching || '--'}</td>
        <td class="text-right p-3 text-white">${player.tackling || '--'}</td>
        <td class="text-right p-3 text-white">${player.awareness || '--'}</td>
        <td class="text-right p-3 text-white">${player.potential || '--'}</td>
        <td class="text-right p-3 text-white">${player.stamina || '--'}</td>
        <td class="text-right p-3 text-white">${player.injury || '--'}</td>
        <td class="text-right p-3 text-white">${player.morale || '--'}</td>
        <td class="text-right p-3 text-white">${player.age || '--'}</td>
        <td class="text-right p-3 text-white">${player.contract || '--'}</td>
        <td class="text-right p-3 text-white">${player.years || '--'}</td>
        <td class="text-left p-3 text-[#94a3b8]">${player.depth || '--'}</td>
        <td class="text-left p-3">
          <span class="px-2 py-0.5 rounded text-xs ${getHealthColorClass(player.health)}">
            ${player.health || 'Healthy'}
          </span>
        </td>
        <td class="text-center p-3">
          ${player.trade_block ? '<span class="inline-block w-2 h-2 rounded-full bg-[#d4af37]"></span>' : ''}
        </td>
      </tr>
    `).join('');
    
    rosterTableBody.innerHTML = html;
  }

  /**
   * Render depth chart with dropdowns
   */
  function renderDepthChart() {
    if (!depthBox) return;
    
    if (!depthChartData || !depthChartData.slots) {
      renderEmptyDepthChart();
      return;
    }
    
    // Group slots by position
    const byPos = {};
    for (const slot of depthChartData.slots) {
      const position = slot.position;
      if (!byPos[position]) {
        byPos[position] = [];
      }
      byPos[position].push(slot);
    }
    
    const html = Object.keys(byPos)
      .sort()
      .map(pos => {
        const slots = byPos[pos].sort((a, b) => a.slot.localeCompare(b.slot));
        
        const rows = slots.map(slot => {
          const dropdown = createPlayerDropdown(slot);
          playerDropdowns.set(slot.slot, dropdown);
          
          return `
            <tr class="hover:bg-[#2d4a6f]/20 transition-colors">
              <td class="slot text-[#94a3b8] font-medium p-2">${slot.slot}</td>
              <td class="name p-2">${dropdown}</td>
            </tr>
          `;
        }).join('');
        
        return `
          <div class="pos-group">
            <div class="pos-header">
              <span class="pos-title">${pos}</span>
              <span class="pos-count">${slots.filter(s => s.player_id).length}/${slots.length}</span>
            </div>
            <table class="pos-table">
              <tbody>
                ${rows}
              </tbody>
            </table>
          </div>
        `;
      }).join('');
    
    depthBox.innerHTML = `<div class="depth-grid">${html}</div>`;
  }

  /**
   * Create player dropdown for a slot
   */
  function createPlayerDropdown(slot) {
    const currentPlayerId = slot.player_id;
    const currentPlayerName = slot.name;
    const currentPlayerOvr = slot.ovr;
    
    // Get players for this position
    const positionPlayers = rosterData.filter(p => p.position === slot.position);
    
    // Sort by OVR desc
    positionPlayers.sort((a, b) => (b.overall_rating || 0) - (a.overall_rating || 0));
    
    let options = '<option value="">Empty</option>';
    
    positionPlayers.forEach(player => {
      const selected = player.id === currentPlayerId ? 'selected' : '';
      const disabled = isPlayerUsedInGroup(player.id, slot.slot) ? 'disabled' : '';
      const tooltip = disabled ? 'title="Already used in this position group"' : '';
      
      options += `
        <option value="${player.id}" ${selected} ${disabled} ${tooltip}>
          ${player.name} [${player.overall_rating || '--'}]
        </option>
      `;
    });
    
    return `
      <select class="depth-dropdown w-full" 
              data-slot="${slot.slot}" 
              data-position="${slot.position}"
              onchange="handleSlotChange(this)">
        ${options}
      </select>
      <div class="validation-error" id="error-${slot.slot}" style="display: none;"></div>
    `;
  }

  /**
   * Check if player is already used in the same position group
   */
  function isPlayerUsedInGroup(playerId, currentSlot) {
    if (!depthChartData || !depthChartData.slots) return false;
    
    const currentGroup = getPositionGroup(currentSlot);
    if (!currentGroup) return false;
    
    return depthChartData.slots.some(slot => 
      slot.player_id === playerId && 
      slot.slot !== currentSlot && 
      getPositionGroup(slot.slot) === currentGroup
    );
  }

  /**
   * Get position group for a slot
   */
  function getPositionGroup(slot) {
    const groups = {
      'QB': ['QB1', 'QB2'],
      'RB': ['RB1', 'RB2'],
      'WR': ['WR1', 'WR2', 'WR3'],
      'TE': ['TE1', 'TE2'],
      'LT': ['LT'], 'LG': ['LG'], 'C': ['C'], 'RG': ['RG'], 'RT': ['RT'],
      'LDE': ['LDE'], 'DT': ['DT'], 'RDE': ['RDE'],
      'MLB': ['MLB1', 'MLB2'], 'OLB': ['OLB1', 'OLB2'],
      'CB': ['CB1', 'CB2', 'CB3'], 'FS': ['FS'], 'SS': ['SS'],
      'K': ['K'], 'P': ['P'],
      'KR': ['KR1', 'KR2'], 'PR': ['PR1', 'PR2']
    };
    
    for (const [group, slots] of Object.entries(groups)) {
      if (slots.includes(slot)) {
        return group;
      }
    }
    return slot;
  }

  /**
   * Handle dropdown change
   */
  async function handleSlotChange(dropdown) {
    const slot = dropdown.dataset.slot;
    const position = dropdown.dataset.position;
    const playerId = dropdown.value ? parseInt(dropdown.value) : null;
    
    // Clear any existing error
    clearSlotError(slot);
    
    try {
      const response = await fetch(`/api/teams/${teamId}/depthchart/slot`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          season,
          position,
          slot,
          player_id: playerId
        })
      });
      
      if (!response.ok) {
        if (response.status === 409) {
          const errorData = await response.json();
          showSlotError(slot, errorData.detail);
          // Revert dropdown to previous value
          dropdown.value = depthChartData.slots.find(s => s.slot === slot)?.player_id || '';
          return;
        }
        throw new Error(`HTTP ${response.status}`);
      }
      
      // Update local data
      const updatedChart = await response.json();
      depthChartData = updatedChart;
      
      // Update all dropdowns to reflect new state
      updateAllDropdowns();
      
      // Show success feedback
      showToast(`Updated ${slot}`, 'success');
      
    } catch (error) {
      console.error('Failed to update slot:', error);
      showSlotError(slot, 'Failed to update slot');
      // Revert dropdown
      dropdown.value = depthChartData.slots.find(s => s.slot === slot)?.player_id || '';
    }
  }

  /**
   * Update all dropdowns after a change
   */
  function updateAllDropdowns() {
    playerDropdowns.forEach((dropdown, slot) => {
      const slotData = depthChartData.slots.find(s => s.slot === slot);
      if (slotData) {
        // Update options to disable used players
        updateDropdownOptions(dropdown, slot);
      }
    });
  }

  /**
   * Update dropdown options to disable used players
   */
  function updateDropdownOptions(dropdown, currentSlot) {
    const position = dropdown.dataset.position;
    const currentValue = dropdown.value;
    
    // Get players for this position
    const positionPlayers = rosterData.filter(p => p.position === position);
    positionPlayers.sort((a, b) => (b.overall_rating || 0) - (a.overall_rating || 0));
    
    let options = '<option value="">Empty</option>';
    
    positionPlayers.forEach(player => {
      const selected = player.id.toString() === currentValue ? 'selected' : '';
      const disabled = isPlayerUsedInGroup(player.id, currentSlot) ? 'disabled' : '';
      const tooltip = disabled ? 'title="Already used in this position group"' : '';
      
      options += `
        <option value="${player.id}" ${selected} ${disabled} ${tooltip}>
          ${player.name} [${player.overall_rating || '--'}]
        </option>
      `;
    });
    
    dropdown.innerHTML = options;
  }

  /**
   * Show slot validation error
   */
  function showSlotError(slot, message) {
    const errorDiv = document.getElementById(`error-${slot}`);
    if (errorDiv) {
      errorDiv.textContent = message;
      errorDiv.style.display = 'block';
    }
  }

  /**
   * Clear slot validation error
   */
  function clearSlotError(slot) {
    const errorDiv = document.getElementById(`error-${slot}`);
    if (errorDiv) {
      errorDiv.style.display = 'none';
    }
  }

  /**
   * Auto-fill empty slots
   */
  async function autoFill() {
    if (!btnAuto) return;
    
    // Show loading state
    const originalText = btnAuto.textContent;
    btnAuto.textContent = 'Auto-Filling...';
    btnAuto.disabled = true;
    
    // Hide previous warnings
    hideWarnings();
    
    try {
      const response = await fetch(`/api/teams/${teamId}/depthchart/auto_fill`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ season })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.success && data.depth_chart) {
        // Update local data
        depthChartData = data.depth_chart;
        
        // Re-render depth chart
        renderDepthChart();
        
        // Show warnings if any
        if (data.depth_chart.warnings && data.depth_chart.warnings.length > 0) {
          showWarnings(data.depth_chart.warnings);
        }
        
        showToast('Auto-fill completed', 'success');
      } else {
        throw new Error(data.message || 'Auto-fill failed');
      }
      
    } catch (error) {
      console.error('Auto-fill error:', error);
      showToast(`Auto-fill failed: ${error.message}`, 'error');
    } finally {
      // Restore button state
      btnAuto.textContent = originalText;
      btnAuto.disabled = false;
    }
  }

  /**
   * Show warnings
   */
  function showWarnings(warnings) {
    if (!warningsBar || !warningsList) return;
    
    const html = warnings.map(warning => 
      `<div class="warning-item">• ${warning}</div>`
    ).join('');
    
    warningsList.innerHTML = html;
    warningsBar.style.display = 'block';
  }

  /**
   * Hide warnings
   */
  function hideWarnings() {
    if (warningsBar) {
      warningsBar.style.display = 'none';
    }
  }

  /**
   * Render empty depth chart state
   */
  function renderEmptyDepthChart() {
    if (!depthBox) return;
    
    depthBox.innerHTML = `
      <div class="empty text-center text-[#94a3b8] py-8">
        <div class="mb-4">
          <svg class="mx-auto h-12 w-12 text-[#94a3b8]/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </div>
        <p class="text-lg font-medium mb-2">No depth chart yet</p>
        <p class="text-sm">Select players manually or click Auto-Fill to generate one</p>
      </div>
    `;
  }

  /**
   * Show toast notification
   */
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 px-4 py-3 rounded-lg shadow-lg z-50 transition-all duration-300 ${
      type === 'success' ? 'bg-green-600 text-white' :
      type === 'error' ? 'bg-red-600 text-white' :
      'bg-blue-600 text-white'
    }`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
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
   * Get health color class
   */
  function getHealthColorClass(status) {
    switch (status) {
      case 'Healthy': return 'bg-green-500/20 text-green-400';
      case 'Q': return 'bg-amber-500/20 text-amber-400';
      case 'D': return 'bg-red-500/20 text-red-400';
      case 'O': return 'bg-gray-500/20 text-gray-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  }

  /**
   * Get mock roster data
   */
  function getMockRoster() {
    return [
      {"id": 212, "name": "J. Kingsley", "position": "QB", "overall_rating": 84, "speed": 78, "strength": 62, "agility": 82, "throw_power": 91, "throw_accuracy": 86, "catching": 48, "tackling": 22, "awareness": 85, "potential": 88, "stamina": 92, "injury": 18, "morale": 74, "age": 28, "contract": "$8.5M", "years": 2, "depth": "QB1", "health": "Healthy", "trade_block": false, "number": 12},
      {"id": 213, "name": "M. Sanders", "position": "QB", "overall_rating": 71, "speed": 75, "strength": 58, "agility": 79, "throw_power": 85, "throw_accuracy": 82, "catching": 45, "tackling": 20, "awareness": 78, "potential": 82, "stamina": 88, "injury": 22, "morale": 68, "age": 24, "contract": "$2.1M", "years": 1, "depth": "QB2", "health": "Healthy", "trade_block": false, "number": 8},
      {"id": 332, "name": "T. Morrow", "position": "RB", "overall_rating": 82, "speed": 85, "strength": 78, "agility": 88, "throw_power": 35, "throw_accuracy": 25, "catching": 72, "tackling": 45, "awareness": 79, "potential": 85, "stamina": 89, "injury": 15, "morale": 82, "age": 26, "contract": "$5.2M", "years": 3, "depth": "RB1", "health": "Healthy", "trade_block": false, "number": 34},
      {"id": 411, "name": "K. Carter", "position": "RB", "overall_rating": 76, "speed": 82, "strength": 75, "agility": 85, "throw_power": 30, "throw_accuracy": 22, "catching": 68, "tackling": 42, "awareness": 74, "potential": 83, "stamina": 86, "injury": 18, "morale": 78, "age": 23, "contract": "$1.8M", "years": 2, "depth": "RB2", "health": "Healthy", "trade_block": false, "number": 28},
      {"id": 101, "name": "K. Benton", "position": "WR", "overall_rating": 87, "speed": 88, "strength": 65, "agility": 92, "throw_power": 40, "throw_accuracy": 35, "catching": 94, "tackling": 35, "awareness": 86, "potential": 90, "stamina": 85, "injury": 12, "morale": 88, "age": 27, "contract": "$12.5M", "years": 4, "depth": "WR1", "health": "Healthy", "trade_block": false, "number": 84},
      {"id": 234, "name": "L. Carter", "position": "WR", "overall_rating": 83, "speed": 86, "strength": 62, "agility": 89, "throw_power": 38, "throw_accuracy": 32, "catching": 91, "tackling": 32, "awareness": 82, "potential": 87, "stamina": 83, "injury": 16, "morale": 85, "age": 25, "contract": "$8.9M", "years": 3, "depth": "WR2", "health": "Healthy", "trade_block": false, "number": 11},
      {"id": 456, "name": "J. Thomas", "position": "WR", "overall_rating": 74, "speed": 84, "strength": 58, "agility": 87, "throw_power": 35, "throw_accuracy": 28, "catching": 85, "tackling": 28, "awareness": 76, "potential": 85, "stamina": 80, "injury": 20, "morale": 72, "age": 22, "contract": "$2.3M", "years": 2, "depth": "WR3", "health": "Healthy", "trade_block": false, "number": 17}
    ];
  }

  /**
   * Initialize event listeners
   */
  function initializeEventListeners() {
    // Auto-fill button click
    if (btnAuto) {
      btnAuto.addEventListener('click', async (e) => {
        e.preventDefault();
        const confirmed = window.confirm('Auto-fill empty slots only? This will not overwrite your manual selections.');
        if (confirmed) {
          await autoFill();
        }
      });
    }
  }

  // Make handleSlotChange globally available
  window.handleSlotChange = handleSlotChange;

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initializeEventListeners();
      initialize();
    });
  } else {
    initializeEventListeners();
    initialize();
  }

  // Expose functions globally for external use
  window.rosterPage = {
    loadDepthChart,
    autoFill,
    showToast,
    renderDepthChart
  };

})();