# Entity Modal System - README

## Overview

The Entity Modal System provides a global "click name → open card modal" behavior for Players and Coaches across the entire Franchise Football application. This system enables consistent modal interactions without full page reloads while maintaining accessibility and progressive enhancement.

## Data Attribute Contract

### Semantic Markup

Any player or coach name rendered in the application should be wrapped with an anchor tag following this contract:

```html
<!-- Player Links -->
<a href="/players/{id}" data-entity="player" data-id="{id}" class="entity-link">
  Player Name
</a>

<!-- Coach Links -->
<a href="/coaches/{id}" data-entity="coach" data-id="{id}" class="entity-link">
  Coach Name
</a>
```

### Required Attributes

- **`href`**: Canonical URL to the full page (`/players/{id}` or `/coaches/{id}`)
- **`data-entity`**: Entity type (`"player"` or `"coach"`)
- **`data-id`**: Unique identifier (numeric or string)
- **`class="entity-link"**: Required CSS class for event delegation

### Examples

```html
<a href="/players/1234" data-entity="player" data-id="1234" class="entity-link">QB John Sample</a>
<a href="/coaches/77" data-entity="coach" data-id="77" class="entity-link">HC Pat Sample</a>
```

## Implementation Details

### Client Script

The system uses a single ES module (`/app/ui/static/js/entity-modal.js`) that:

1. **Event Delegation**: Listens for clicks on `.entity-link` elements
2. **Progressive Enhancement**: Falls back to navigation if fetch fails
3. **Accessibility**: Manages focus trapping and keyboard navigation
4. **Modal Management**: Handles backdrop clicks, escape key, and close button

### Server Support

API endpoints support a `modal=1` query parameter:

- **`/players/{id}?modal=1`**: Returns modal HTML fragment
- **`/coaches/{id}?modal=1`**: Returns modal HTML fragment
- **Without `modal=1`**: Returns full page (existing behavior)

### Modal Shell

A reusable modal shell is automatically created:

```html
<div id="entity-modal" role="dialog" aria-modal="true" hidden>
  <div class="modal-backdrop"></div>
  <div class="modal-panel" role="document">
    <button class="modal-close" aria-label="Close">×</button>
    <div class="modal-content"></div>
  </div>
</div>
```

## Usage Across Pages

The system works consistently across all pages mentioned in the sitemap:

- Dashboard
- Roster
- Depth Chart
- Free Agents
- Trading Block
- Staff
- Stats
- Playoffs
- Draft
- Calendar
- Hall of Fame

### Roster Table Integration

The roster table now uses entity links for player names:

```jsx
<a
  href={`/players/${player.id}`}
  data-entity="player"
  data-id={player.id}
  className="entity-link text-white hover:text-[#d4af37] transition-colors"
>
  {player.name}
</a>
```

## Accessibility Features

- **Focus Management**: Focus trapped within modal, restored to triggering element on close
- **Keyboard Navigation**: Escape key closes modal, Tab navigation within modal
- **Screen Reader Support**: Proper ARIA attributes (`role="dialog"`, `aria-modal="true"`)
- **Loading States**: `aria-busy="true"` during content loading

## Progressive Enhancement

The system gracefully degrades:

1. **JavaScript Disabled**: Links work normally (full page navigation)
2. **Fetch Fails**: Automatically falls back to `window.location.href`
3. **Network Error**: Shows error state and falls back to navigation

## Styling

Modal styles are in `/app/ui/static/css/modal.css`:

- Responsive design (mobile-friendly)
- Dark theme matching application
- Smooth animations and transitions
- High contrast mode support
- Reduced motion support

## Stamina Attribute Clarification

Per requirements, stamina has been clarified to have **minor in-game performance impact only**:

- Moved to separate "Conditioning" category in player cards
- Added tooltip clarification: "Minor in-game performance impact only"
- Added visual indicators in injury tab
- Updated column definitions with clarifying tooltips

## Testing

Comprehensive test suite covers:

- Click event handling
- Modal opening/closing
- Focus management
- Error handling and fallbacks
- Accessibility features
- Performance considerations

## Integration

### Include in Base Template

Add to your base HTML template:

```html
<link rel="stylesheet" href="/static/css/modal.css">
<script type="module" src="/static/js/entity-modal.js"></script>
```

### Programmatic Usage

```javascript
// Open player modal
window.entityModal.openPlayer('123');

// Open coach modal
window.entityModal.openCoach('77');
```

## Browser Support

- Modern browsers with ES6 module support
- Event delegation works with server-side rendered content
- Compatible with paginated/sorted tables
- Works with dynamically injected content

## Performance

- Single event listener on document (event delegation)
- Lazy modal shell creation
- Efficient focus management
- Minimal DOM manipulation

## Future Extensibility

The modal shell is designed to be reusable for other entities:

- Team cards
- Stadium information
- League records
- Any other entity that needs modal display

Simply follow the same data attribute contract with appropriate `data-entity` values and corresponding API endpoints.
