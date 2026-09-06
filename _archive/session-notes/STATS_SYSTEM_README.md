# Franchise Football Stats System

## Overview

The Franchise Football Stats System provides comprehensive statistical tracking and analysis for the football simulation. It includes PBP (Play-by-Play) emission with defensive participants, stats rollup and materialization, validation, and complete API endpoints.

## Architecture

### Core Components

1. **PBP Emission** (`app/routers/sim.py`)
   - Enhanced `_simulate_pbp_for_game_v2` function
   - Emits defensive participant data (tacklers, coverage, pressure, etc.)
   - Maintains realistic game flow and statistics

2. **Stats Models** (`app/models/stats.py`)
   - `PlayerGameStats`: Individual player game statistics
   - `TeamGameStats`: Team game statistics
   - `PlayerSeasonStats`: Player season aggregates
   - `TeamSeasonStats`: Team season aggregates
   - `PlayerCareerStats`: Player career totals

3. **Stats Services** (`app/services/stats/`)
   - `rollup.py`: Post-game stats rollup
   - `materializer.py`: Season/career materialization
   - `validator.py`: Data consistency validation

4. **API Endpoints** (`app/routers/stats.py`)
   - Box score retrieval
   - Statistical leaders
   - Player/team season stats
   - Defense statistics

5. **CLI Tools** (`stats_cli.py`)
   - Command-line interface for stats operations
   - Rollup, materialization, validation commands

## Features

### PBP v2 Enhancement

The enhanced PBP system includes:

- **Defensive Participants**: Every play can include defensive participant IDs
- **Coverage Stats**: Targets, completions allowed, yards allowed, YAC allowed
- **Pressure Stats**: QB hits, pressures, blitzes
- **Tackling Stats**: Solo tackles, assist tackles, missed tackles
- **Turnover Stats**: Interceptions, fumbles, forced fumbles, recoveries
- **Penalty Stats**: Penalty flags, yards, automatic first downs

### Stats Rollup

Post-game processing that aggregates PBP data into:

- **Player Game Stats**: Individual player performance
- **Team Game Stats**: Team performance metrics
- **Derived Stats**: Completion percentage, YPA, YPC, passer rating, etc.

### Stats Materialization

Season and career aggregation:

- **Player Season Stats**: Season totals and averages
- **Team Season Stats**: Team season performance
- **Player Career Stats**: Career totals and records

### Validation

Data consistency checks:

- **Team Stats**: Sum of player stats equals team stats
- **Yardage Consistency**: Pass + rush yards = total yards
- **Turnover Tracking**: Proper turnover attribution
- **Score Reconciliation**: Game scores match PBP events

## API Endpoints

### Box Score
```
GET /api/stats/games/{game_id}
```
Returns complete box score with team and player stats.

### Statistical Leaders
```
GET /api/stats/leaders?year={season}&stat={statistic}&top={count}
```
Returns top performers for a given statistic.

### Player Season Stats
```
GET /api/stats/players/season?year={season}&team={team_id}&position={position}
```
Returns player season statistics with filtering options.

### Team Season Stats
```
GET /api/stats/teams/season?year={season}&conference={conf}&division={div}
```
Returns team season statistics with filtering options.

### Defense Stats
```
GET /api/sim/defense/team-stats/{season}
GET /api/sim/defense/team-stats/{season}/{week}
GET /api/sim/defense/player-stats/{season}
GET /api/sim/defense/player-stats/{season}/{week}
```
Returns defensive statistics at team and player levels.

## Usage

### CLI Commands

```bash
# Roll up stats for a specific game
python stats_cli.py rollup 1

# Materialize season stats
python stats_cli.py materialize 2025

# Validate stats consistency
python stats_cli.py validate 2025
python stats_cli.py validate 2025 --game 1

# Show statistical leaders
python stats_cli.py leaders 2025 pass_yards --top 10

# Show team statistics
python stats_cli.py teams 2025
```

### Makefile Targets

```bash
# Stats operations
make stats-rollup GAME_ID=1
make stats-materialize SEASON=2025
make stats-validate SEASON=2025
make stats-leaders SEASON=2025 STAT=pass_yards TOP=10
make stats-teams SEASON=2025
make stats-test
```

### Testing

```bash
# Run comprehensive stats test
python comprehensive_stats_test.py

# Test specific components
python -m pytest tests/test_stats_rollup.py
python -m pytest tests/test_stats_materializer.py
python -m pytest tests/test_stats_validator.py
```

## Data Flow

1. **Simulation**: PBP v2 generates events with defensive participants
2. **Rollup**: Post-game processing aggregates PBP into player/team game stats
3. **Materialization**: Season/career stats are built from game stats
4. **Validation**: Consistency checks ensure data integrity
5. **API**: Endpoints provide access to all statistical data

## Configuration

### Environment Variables

- `USE_PBP_V2=true`: Enable PBP v2 with defensive participants
- `HFA_POINTS=1.4`: Home field advantage points
- `LEAGUE_SEED=2025`: Base seed for deterministic simulation

### Database

The stats system uses SQLModel with SQLite:

- **Tables**: Auto-created from SQLModel definitions
- **Migrations**: Not required (schema changes handled automatically)
- **Indexing**: Optimized for common queries (season, team, player)

## Performance

### Optimization Features

- **Batch Processing**: Efficient bulk operations
- **Caching**: Materialized stats avoid recalculation
- **Indexing**: Database indexes for fast queries
- **Lazy Loading**: On-demand data retrieval

### Benchmarks

- **Rollup**: ~100ms per game
- **Materialization**: ~2s per season
- **Validation**: ~500ms per season
- **API Response**: <50ms for most endpoints

## Testing

### Test Coverage

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Load and stress testing
- **Validation Tests**: Data consistency verification

### Test Files

- `tests/test_stats_rollup.py`: Rollup functionality
- `tests/test_stats_materializer.py`: Materialization logic
- `tests/test_stats_validator.py`: Validation rules
- `tests/test_stats_api.py`: API endpoint testing
- `comprehensive_stats_test.py`: Full system test

## Troubleshooting

### Common Issues

1. **Missing Stats**: Ensure PBP v2 is enabled and games are simulated
2. **Validation Failures**: Check for data inconsistencies in PBP events
3. **Performance Issues**: Verify database indexes and query optimization
4. **API Errors**: Check server status and endpoint availability

### Debug Commands

```bash
# Check server status
curl http://127.0.0.1:8015/diag/health

# Test PBP data
curl http://127.0.0.1:8015/api/sim/pbp-v2/2025/1

# Test stats API
curl http://127.0.0.1:8015/api/stats/games/1
```

## Future Enhancements

### Planned Features

1. **Advanced Analytics**: EPA, success rate, explosive plays
2. **Historical Comparisons**: Season-over-season analysis
3. **Predictive Modeling**: Performance forecasting
4. **Real-time Updates**: Live stats during simulation
5. **Export Features**: CSV/JSON data export

### Integration Opportunities

1. **Dashboard Integration**: Real-time stats display
2. **Mobile App**: Stats access on mobile devices
3. **Third-party APIs**: Integration with external stats services
4. **Machine Learning**: Advanced statistical analysis

## Contributing

### Development Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Enable PBP v2: `export USE_PBP_V2=true`
3. Run tests: `pytest tests/`
4. Start server: `uvicorn app.main:app --reload --port 8015`

### Code Standards

- **Type Hints**: All functions must have type annotations
- **Documentation**: Docstrings for all public functions
- **Testing**: Unit tests for all new functionality
- **Validation**: Data consistency checks for all operations

### Pull Request Process

1. Create feature branch
2. Implement changes with tests
3. Run full test suite
4. Submit pull request with description
5. Address review feedback
6. Merge after approval

## License

This project is licensed under the MIT License - see the LICENSE file for details.
