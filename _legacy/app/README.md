# Franchise Football

A comprehensive NFL franchise simulation game with realistic gameplay mechanics, player management, and season progression.

## Features

- **Team Management**: Build and manage NFL franchises with realistic rosters
- **Season Simulation**: Play through complete NFL seasons with playoffs
- **Player Stats**: Detailed per-player statistics with depth chart usage distribution
- **Contract System**: Manage player contracts and salary cap
- **Playoffs**: Full playoff bracket system with Super Bowl
- **Offseason**: Free agency, draft, and roster management

## QA & E2E

- Run all tests with coverage gate (≥85% on engine/services):
```
make qa
```
- End-to-end smoke:
```
make e2e
```

## Docker

Build & run:
```
make docker-build
make docker-run
```
Visit http://localhost:8015/

## Development

- Run integrity checks:
```
make integrity
```
- Check diagnostics:
```
make diag
```

