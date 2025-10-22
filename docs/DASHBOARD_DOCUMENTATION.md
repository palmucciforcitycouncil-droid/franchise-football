# Franchise Football Dashboard Documentation

This document contains the technical documentation for the Franchise Football Dashboard v3.1.

## Overview

The dashboard provides a comprehensive view of franchise football data including:
- Division standings
- Power rankings
- Team schedules
- Scouting information
- Box scores

## API Integration

The dashboard connects to the FastAPI backend at `http://127.0.0.1:8015/api/v1` with 2-second timeout for demo-friendly UX.

## Demo Data

All widgets include demo data fallbacks that activate when:
- API is unavailable
- API returns empty responses
- Network timeouts occur

## Components

### DivisionStandings.tsx
- Fetches AFC East standings
- Shows demo tag when using fallback data
- Right-aligned numeric columns

### LeaguePowerRankings.tsx
- Displays all 32 teams in power rankings
- 5 visible rows with internal scroll
- Shows rank changes with delta indicators

### TeamSchedule.tsx
- Team-specific schedule view
- Sticky header with vertical scroll
- Right-aligned W/L indicators

### ScoutingPanel.tsx
- Overview and Tendencies tabs
- Visual progress bars for percentages
- Injury status indicators

### BoxScore.tsx
- Game-specific box scores
- Team identifiers replace HOME/AWAY labels
- Quarter-by-quarter breakdown

