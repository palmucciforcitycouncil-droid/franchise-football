/**
 * Entity Modal Handler - Global click-to-modal behavior for players and coaches
 * 
 * Usage: Wrap player/coach names with:
 * <a href="/players/123" data-entity="player" data-id="123" class="entity-link">Player Name</a>
 * <a href="/coaches/77" data-entity="coach" data-id="77" class="entity-link">Coach Name</a>
 */

class EntityModal {
  constructor() {
    this.modal = null;
    this.lastFocusedElement = null;
    this.isOpen = false;
    this.init();
  }

  init() {
    this.createModalShell();
    this.bindEvents();
  }

  createModalShell() {
    // Check if modal already exists
    if (document.getElementById('entity-modal')) {
      this.modal = document.getElementById('entity-modal');
      return;
    }

    const modalHTML = `
      <div id="entity-modal" role="dialog" aria-modal="true" hidden>
        <div class="modal-backdrop"></div>
        <div class="modal-panel" role="document">
          <button class="modal-close" aria-label="Close modal">×</button>
          <div class="modal-content"></div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    this.modal = document.getElementById('entity-modal');
  }

  bindEvents() {
    // Event delegation for entity links
    document.addEventListener('click', (e) => {
      const entityLink = e.target.closest('.entity-link');
      if (!entityLink) return;

      e.preventDefault();
      this.handleEntityClick(entityLink);
    });

    // Modal close events
    if (this.modal) {
      this.modal.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal-backdrop') || 
            e.target.classList.contains('modal-close')) {
          this.closeModal();
        }
      });

      // Escape key handler
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.isOpen) {
          this.closeModal();
        }
      });
    }
  }

  async handleEntityClick(entityLink) {
    const entity = entityLink.dataset.entity;
    const id = entityLink.dataset.id;
    const href = entityLink.href;

    if (!entity || !id) {
      console.warn('Entity link missing required data attributes:', entityLink);
      window.location.href = href;
      return;
    }

    // Store the triggering element for focus restoration
    this.lastFocusedElement = entityLink;

    // Show modal with loading state
    this.showModal();
    this.setLoadingState(true);

    try {
      // Determine endpoint
      let endpoint;
      switch (entity) {
        case 'player':
          endpoint = `/players/${id}?modal=1`;
          break;
        case 'coach':
          endpoint = `/coaches/${id}?modal=1`;
          break;
        default:
          throw new Error(`Unknown entity type: ${entity}`);
      }

      // Fetch modal content
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const html = await response.text();
      this.setModalContent(html);
      this.setLoadingState(false);

    } catch (error) {
      console.warn('Failed to load modal content, falling back to navigation:', error);
      this.closeModal();
      window.location.href = href;
    }
  }

  showModal() {
    if (!this.modal) return;

    this.modal.hidden = false;
    this.isOpen = true;
    
    // Lock body scroll
    document.body.style.overflow = 'hidden';
    
    // Focus the close button for accessibility
    setTimeout(() => {
      const closeButton = this.modal.querySelector('.modal-close');
      if (closeButton) {
        closeButton.focus();
      }
    }, 100);
  }

  closeModal() {
    if (!this.modal) return;

    this.modal.hidden = true;
    this.isOpen = false;
    
    // Restore body scroll
    document.body.style.overflow = '';
    
    // Restore focus to triggering element
    if (this.lastFocusedElement) {
      this.lastFocusedElement.focus();
      this.lastFocusedElement = null;
    }

    // Clear modal content
    this.setModalContent('');
  }

  setModalContent(html) {
    const content = this.modal.querySelector('.modal-content');
    if (content) {
      content.innerHTML = html;
    }
  }

  setLoadingState(loading) {
    const content = this.modal.querySelector('.modal-content');
    if (content) {
      content.setAttribute('aria-busy', loading.toString());
      
      if (loading) {
        content.innerHTML = `
          <div class="modal-loading">
            <div class="spinner"></div>
            <p>Loading...</p>
          </div>
        `;
      }
    }
  }

  // Public API for programmatic control
  openPlayer(id) {
    const mockLink = document.createElement('a');
    mockLink.dataset.entity = 'player';
    mockLink.dataset.id = id;
    mockLink.href = `/players/${id}`;
    mockLink.className = 'entity-link';
    
    this.handleEntityClick(mockLink);
  }

  openCoach(id) {
    const mockLink = document.createElement('a');
    mockLink.dataset.entity = 'coach';
    mockLink.dataset.id = id;
    mockLink.href = `/coaches/${id}`;
    mockLink.className = 'entity-link';
    
    this.handleEntityClick(mockLink);
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.entityModal = new EntityModal();
  });
} else {
  window.entityModal = new EntityModal();
}

// Export for module usage if needed
export default EntityModal;
