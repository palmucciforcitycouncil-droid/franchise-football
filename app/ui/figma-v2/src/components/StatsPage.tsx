/**
 * Stats Page Component - Redesigned
 * Professional stats platform with customizable columns
 */

import { useState, useMemo, useRef, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Settings, Download, Search, ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-react';
import { StatColumnChooser, SelectedStat } from './stats/StatColumnChooser';
import { playerStatCategories, teamStatCategories, coachStatCategories } from '../lib/statHierarchy';
import { ClickablePlayerName } from './ui/ClickablePlayerName';
import { ClickableCoachName } from './ui/ClickableCoachName';
import './RosterTable.css';

type StatsTab = 'team' | 'player' | 'coach';
type SortDirection = 'asc' | 'desc' | null;

// Mock data types
interface PlayerData {
  id: string;
  name: string;
  team: string;
  position: string;
  [key: string]: any;
}

interface TeamData {
  id: string;
  team_name: string;
  team_abbr: string;
  conference: string;
  division: string;
  [key: string]: any;
}

interface CoachData {
  id: string;
  coach_name: string;
  coach_role: string;
  coach_team: string;
  [key: string]: any;
}

// Generate mock player data
const generateMockPlayers = (): PlayerData[] => {
  const teams = ['NE', 'BUF', 'MIA', 'NYJ', 'BAL', 'CIN', 'CLE', 'PIT', 'HOU', 'IND', 'JAX', 'TEN'];
  const positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S', 'K', 'P'];
  const firstNames = ['Tom', 'Patrick', 'Aaron', 'Josh', 'Lamar', 'Joe', 'Justin', 'Trevor', 'Tua', 'Mac', 'Jalen', 'Dak'];
  const lastNames = ['Brady', 'Mahomes', 'Rodgers', 'Allen', 'Jackson', 'Burrow', 'Herbert', 'Lawrence', 'Tagovailoa', 'Jones', 'Hurts', 'Prescott'];
  
  return Array.from({ length: 200 }, (_, i) => ({
    id: `player-${i}`,
    player_name: `${firstNames[i % firstNames.length]} ${lastNames[i % lastNames.length]}`,
    name: `${firstNames[i % firstNames.length]} ${lastNames[i % lastNames.length]}`,
    player_team: teams[i % teams.length],
    team: teams[i % teams.length],
    player_pos: positions[i % positions.length],
    position: positions[i % positions.length],
    player_age: 22 + (i % 15),
    games_played: Math.floor(Math.random() * 17) + 1,
    games_started: Math.floor(Math.random() * 17),
    pass_att: Math.floor(Math.random() * 600),
    pass_cmp: Math.floor(Math.random() * 400),
    pass_yds: Math.floor(Math.random() * 5000),
    pass_td: Math.floor(Math.random() * 40),
    pass_int: Math.floor(Math.random() * 15),
    qb_cmp_pct: (Math.random() * 30 + 55).toFixed(1),
    rb_rush_att: Math.floor(Math.random() * 300),
    rb_rush_yds: Math.floor(Math.random() * 1500),
    rb_rush_td: Math.floor(Math.random() * 15),
    targets: Math.floor(Math.random() * 150),
    receptions: Math.floor(Math.random() * 100),
    rec_yds: Math.floor(Math.random() * 1500),
    rec_td: Math.floor(Math.random() * 12),
    tackles_combined: Math.floor(Math.random() * 120),
    sacks: (Math.random() * 15).toFixed(1),
    interceptions: Math.floor(Math.random() * 6),
  }));
};

// Generate mock team data
const generateMockTeams = (): TeamData[] => {
  const teams = [
    { name: 'New England Patriots', abbr: 'NE', conf: 'AFC', div: 'East' },
    { name: 'Buffalo Bills', abbr: 'BUF', conf: 'AFC', div: 'East' },
    { name: 'Miami Dolphins', abbr: 'MIA', conf: 'AFC', div: 'East' },
    { name: 'New York Jets', abbr: 'NYJ', conf: 'AFC', div: 'East' },
    { name: 'Baltimore Ravens', abbr: 'BAL', conf: 'AFC', div: 'North' },
    { name: 'Cincinnati Bengals', abbr: 'CIN', conf: 'AFC', div: 'North' },
    { name: 'Cleveland Browns', abbr: 'CLE', conf: 'AFC', div: 'North' },
    { name: 'Pittsburgh Steelers', abbr: 'PIT', conf: 'AFC', div: 'North' },
  ];

  return teams.map((team, i) => ({
    id: `team-${i}`,
    team_name: team.name,
    team_abbr: team.abbr,
    conference: team.conf,
    division: team.div,
    wins: Math.floor(Math.random() * 12) + 3,
    losses: Math.floor(Math.random() * 12) + 3,
    ties: 0,
    points_for: Math.floor(Math.random() * 200) + 300,
    points_against: Math.floor(Math.random() * 200) + 300,
    off_yds: Math.floor(Math.random() * 2000) + 4000,
    team_pass_yds: Math.floor(Math.random() * 2000) + 3000,
    team_rush_yds: Math.floor(Math.random() * 1000) + 1500,
  }));
};

// Generate mock coach data
const generateMockCoaches = (): CoachData[] => {
  const teams = ['NE', 'BUF', 'MIA', 'NYJ', 'BAL', 'CIN', 'CLE', 'PIT'];
  const roles = ['HC', 'OC', 'DC'];
  const names = ['Bill Belichick', 'Sean McDermott', 'Mike McDaniel', 'Robert Saleh', 'John Harbaugh', 'Zac Taylor', 'Kevin Stefanski', 'Mike Tomlin'];

  return teams.flatMap((team, i) => 
    roles.map((role, j) => {
      const coachName = role === 'HC' ? names[i] : `${names[i].split(' ')[1]} ${role}`;
      const age = 40 + Math.floor(Math.random() * 25);
      const exp = Math.floor(Math.random() * 15) + 3;
      const wins = role === 'HC' ? Math.floor(Math.random() * 100) : 0;
      const losses = role === 'HC' ? Math.floor(Math.random() * 80) : 0;
      const winPct = role === 'HC' && (wins + losses) > 0 ? ((wins / (wins + losses)) * 100).toFixed(1) : '0.0';
      
      return {
        id: `coach-${i}-${j}`,
        coach_name: coachName,
        name: coachName, // For ClickableCoachName
        coach_role: role,
        role: role, // For ClickableCoachName
        coach_team: team,
        team: team, // For ClickableCoachName
        coach_age: age,
        age: age, // For ClickableCoachName
        coach_exp: exp,
        hc_wins: wins,
        hc_losses: losses,
        hc_ties: 0,
        hc_win_pct: winPct,
        playoff_app: role === 'HC' ? Math.floor(Math.random() * 10) : 0,
        playoff_wins: role === 'HC' ? Math.floor(Math.random() * 8) : 0,
        super_bowls: role === 'HC' ? Math.floor(Math.random() * 3) : 0,
        avg_points_scored: (Math.random() * 10 + 20).toFixed(1),
        avg_points_allowed: (Math.random() * 10 + 18).toFixed(1),
        turnover_diff: (Math.random() * 20 - 10).toFixed(0),
        avg_yards_per_game: (Math.random() * 100 + 300).toFixed(0),
      };
    })
  );
};

// Default selected stats for each tab
const defaultPlayerStats: SelectedStat[] = [
  { id: 'player_name', variable: 'player_name', label: 'Player Name', categoryLabel: 'Core Identity & Participation', subcategoryLabel: 'Identity' },
  { id: 'player_pos', variable: 'player_pos', label: 'Position', categoryLabel: 'Core Identity & Participation', subcategoryLabel: 'Identity' },
  { id: 'player_team', variable: 'player_team', label: 'Team', categoryLabel: 'Core Identity & Participation', subcategoryLabel: 'Identity' },
  { id: 'player_age', variable: 'player_age', label: 'Age', categoryLabel: 'Core Identity & Participation', subcategoryLabel: 'Identity' },
  { id: 'games_played', variable: 'games_played', label: 'Games Played', categoryLabel: 'Core Identity & Participation', subcategoryLabel: 'Participation' },
];

const defaultTeamStats: SelectedStat[] = [
  { id: 'team_name', variable: 'team_name', label: 'Team Name', categoryLabel: 'Identity & Record', subcategoryLabel: 'Team Identity' },
  { id: 'conference', variable: 'conference', label: 'Conference', categoryLabel: 'Identity & Record', subcategoryLabel: 'Team Identity' },
  { id: 'division', variable: 'division', label: 'Division', categoryLabel: 'Identity & Record', subcategoryLabel: 'Team Identity' },
  { id: 'wins', variable: 'wins', label: 'Wins', categoryLabel: 'Identity & Record', subcategoryLabel: 'Record' },
  { id: 'losses', variable: 'losses', label: 'Losses', categoryLabel: 'Identity & Record', subcategoryLabel: 'Record' },
];

const defaultCoachStats: SelectedStat[] = [
  { id: 'coach_name', variable: 'coach_name', label: 'Coach Name', categoryLabel: 'Coach Identity', subcategoryLabel: 'Identity' },
  { id: 'coach_role', variable: 'coach_role', label: 'Role (HC/OC/DC)', categoryLabel: 'Coach Identity', subcategoryLabel: 'Identity' },
  { id: 'coach_team', variable: 'coach_team', label: 'Team', categoryLabel: 'Coach Identity', subcategoryLabel: 'Identity' },
  { id: 'coach_age', variable: 'coach_age', label: 'Age', categoryLabel: 'Coach Identity', subcategoryLabel: 'Identity' },
];

export function StatsPage() {
  const [activeTab, setActiveTab] = useState<StatsTab>('player');
  const [showColumnChooser, setShowColumnChooser] = useState(false);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [teamFilter, setTeamFilter] = useState('all');
  const [positionFilter, setPositionFilter] = useState('all');
  const [conferenceFilter, setConferenceFilter] = useState('all');
  const [divisionFilter, setDivisionFilter] = useState('all');
  const [roleFilter, setRoleFilter] = useState('all');

  // Sorting
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  // Refs for scroll sync
  const bodyScrollRef = useRef<HTMLDivElement>(null);
  const topScrollbarRef = useRef<HTMLDivElement>(null);
  const tableRef = useRef<HTMLTableElement>(null);

  // Selected stats for each tab
  const [playerSelectedStats, setPlayerSelectedStats] = useState<SelectedStat[]>(defaultPlayerStats);
  const [teamSelectedStats, setTeamSelectedStats] = useState<SelectedStat[]>(defaultTeamStats);
  const [coachSelectedStats, setCoachSelectedStats] = useState<SelectedStat[]>(defaultCoachStats);

  // Mock data
  const playerData = useMemo(() => generateMockPlayers(), []);
  const teamData = useMemo(() => generateMockTeams(), []);
  const coachData = useMemo(() => generateMockCoaches(), []);

  // Get current stats based on tab
  const currentStats = activeTab === 'player' ? playerSelectedStats 
    : activeTab === 'team' ? teamSelectedStats 
    : coachSelectedStats;

  // Get current data based on tab
  const currentData = useMemo(() => {
    let data: any[] = activeTab === 'player' ? playerData 
      : activeTab === 'team' ? teamData 
      : coachData;

    // Apply filters
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      data = data.filter(item => {
        if (activeTab === 'player') {
          return item.player_name?.toLowerCase().includes(query) ||
                 item.player_team?.toLowerCase().includes(query);
        } else if (activeTab === 'team') {
          return item.team_name?.toLowerCase().includes(query) ||
                 item.team_abbr?.toLowerCase().includes(query);
        } else {
          return item.coach_name?.toLowerCase().includes(query) ||
                 item.coach_team?.toLowerCase().includes(query);
        }
      });
    }

    if (activeTab === 'player') {
      if (teamFilter !== 'all') {
        data = data.filter(item => item.player_team === teamFilter);
      }
      if (positionFilter !== 'all') {
        data = data.filter(item => item.player_pos === positionFilter);
      }
    } else if (activeTab === 'team') {
      if (conferenceFilter !== 'all') {
        data = data.filter(item => item.conference === conferenceFilter);
      }
      if (divisionFilter !== 'all') {
        data = data.filter(item => item.division === divisionFilter);
      }
    } else if (activeTab === 'coach') {
      if (teamFilter !== 'all') {
        data = data.filter(item => item.coach_team === teamFilter);
      }
      if (roleFilter !== 'all') {
        data = data.filter(item => item.coach_role === roleFilter);
      }
    }

    // Apply sorting
    if (sortColumn && sortDirection) {
      data = [...data].sort((a, b) => {
        const aVal = a[sortColumn];
        const bVal = b[sortColumn];
        
        // Handle null/undefined values
        if (aVal === null || aVal === undefined || aVal === '-') return 1;
        if (bVal === null || bVal === undefined || bVal === '-') return -1;
        
        // Convert to numbers if possible
        const aNum = parseFloat(aVal);
        const bNum = parseFloat(bVal);
        
        let comparison = 0;
        if (!isNaN(aNum) && !isNaN(bNum)) {
          // Numeric comparison
          comparison = aNum - bNum;
        } else {
          // String comparison
          comparison = String(aVal).localeCompare(String(bVal));
        }
        
        return sortDirection === 'asc' ? comparison : -comparison;
      });
    }

    return data;
  }, [activeTab, playerData, teamData, coachData, searchQuery, teamFilter, positionFilter, conferenceFilter, divisionFilter, roleFilter, sortColumn, sortDirection]);

  const handleApplyStats = (stats: SelectedStat[]) => {
    if (activeTab === 'player') {
      setPlayerSelectedStats(stats);
    } else if (activeTab === 'team') {
      setTeamSelectedStats(stats);
    } else {
      setCoachSelectedStats(stats);
    }
  };

  const handleSort = (variable: string) => {
    if (sortColumn === variable) {
      // Cycle through: asc -> desc -> null
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else if (sortDirection === 'desc') {
        setSortColumn(null);
        setSortDirection(null);
      }
    } else {
      // New column, start with desc (highest first) for numbers, asc for text
      setSortColumn(variable);
      setSortDirection('desc');
    }
  };

  const handleTabChange = (tab: StatsTab) => {
    setActiveTab(tab);
    // Reset sorting when changing tabs
    setSortColumn(null);
    setSortDirection(null);
  };

  const handleExport = () => {
    // Placeholder for export functionality
    alert('Export to Sheets functionality coming soon!');
  };

  const getValue = (item: any, variable: string): any => {
    return item[variable] ?? '-';
  };

  // Sync scrollbars bidirectionally
  useEffect(() => {
    const body = bodyScrollRef.current;
    const topBar = topScrollbarRef.current;
    const table = tableRef.current;
    const sizer = topBar?.querySelector('.sizer') as HTMLElement | null;

    if (!body || !topBar || !sizer || !table) return;

    // Update sizer width to match table scrollWidth
    const setSizerWidth = () => {
      sizer.style.width = table.scrollWidth + 'px';
    };

    // Loop guard for bidirectional sync
    let syncing = false;

    const handleTopBarScroll = () => {
      if (syncing) return;
      syncing = true;
      body.scrollLeft = topBar.scrollLeft;
      syncing = false;
    };

    const handleBodyScroll = () => {
      if (syncing) return;
      syncing = true;
      topBar.scrollLeft = body.scrollLeft;
      syncing = false;
    };

    // Attach listeners
    topBar.addEventListener('scroll', handleTopBarScroll);
    body.addEventListener('scroll', handleBodyScroll);

    // ResizeObserver to keep sizer accurate
    const ro = new ResizeObserver(setSizerWidth);
    ro.observe(table);

    // Also update on window resize and font load
    window.addEventListener('resize', setSizerWidth);
    if (document.fonts?.ready) {
      document.fonts.ready.then(setSizerWidth);
    }

    // Initial width set
    setSizerWidth();

    return () => {
      topBar.removeEventListener('scroll', handleTopBarScroll);
      body.removeEventListener('scroll', handleBodyScroll);
      ro.disconnect();
      window.removeEventListener('resize', setSizerWidth);
    };
  }, [activeTab, currentData.length, currentStats.length]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-white mb-2">Stats</h2>
        <p className="text-[#94a3b8]">
          Customize and analyze comprehensive statistics across teams, players, and coaches
        </p>
      </div>

      {/* Main Stats Box */}
      <div className="roster-card" id="statsCard">
        {/* Tab Navigation */}
        <div className="border-b border-[#2d4a6f]">
          <div className="flex">
            <button
              onClick={() => handleTabChange('team')}
              className={`px-6 py-4 transition-colors relative ${
                activeTab === 'team'
                  ? 'text-white bg-[#0a1929]'
                  : 'text-[#94a3b8] hover:text-white hover:bg-[#0a1929]/50'
              }`}
            >
              Team
              {activeTab === 'team' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#d4af37]" />
              )}
            </button>
            <button
              onClick={() => handleTabChange('player')}
              className={`px-6 py-4 transition-colors relative ${
                activeTab === 'player'
                  ? 'text-white bg-[#0a1929]'
                  : 'text-[#94a3b8] hover:text-white hover:bg-[#0a1929]/50'
              }`}
            >
              Player
              {activeTab === 'player' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#d4af37]" />
              )}
            </button>
            <button
              onClick={() => handleTabChange('coach')}
              className={`px-6 py-4 transition-colors relative ${
                activeTab === 'coach'
                  ? 'text-white bg-[#0a1929]'
                  : 'text-[#94a3b8] hover:text-white hover:bg-[#0a1929]/50'
              }`}
            >
              Coach
              {activeTab === 'coach' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#d4af37]" />
              )}
            </button>
          </div>
        </div>

        {/* Control Bar - Adapts based on active tab */}
        <div className="p-4 border-b border-[#2d4a6f] bg-[#0a1929]">
          <div className="grid grid-cols-[1fr_1fr_1fr_auto_auto] gap-3 items-end">
            {/* Dynamic Filters based on Tab */}
            {activeTab === 'team' && (
              <>
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">Conference</label>
                  <Select value={conferenceFilter} onValueChange={setConferenceFilter}>
                    <SelectTrigger className="bg-[#1a2332] border-[#2d4a6f] text-white">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="AFC">AFC</SelectItem>
                      <SelectItem value="NFC">NFC</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">Division</label>
                  <Select value={divisionFilter} onValueChange={setDivisionFilter}>
                    <SelectTrigger className="bg-[#1a2332] border-[#2d4a6f] text-white">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="East">East</SelectItem>
                      <SelectItem value="North">North</SelectItem>
                      <SelectItem value="South">South</SelectItem>
                      <SelectItem value="West">West</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </>
            )}

            {activeTab === 'player' && (
              <>
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">Team</label>
                  <Select value={teamFilter} onValueChange={setTeamFilter}>
                    <SelectTrigger className="bg-[#1a2332] border-[#2d4a6f] text-white">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="NE">NE</SelectItem>
                      <SelectItem value="BUF">BUF</SelectItem>
                      <SelectItem value="MIA">MIA</SelectItem>
                      <SelectItem value="NYJ">NYJ</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">Position</label>
                  <Select value={positionFilter} onValueChange={setPositionFilter}>
                    <SelectTrigger className="bg-[#1a2332] border-[#2d4a6f] text-white">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="QB">QB</SelectItem>
                      <SelectItem value="RB">RB</SelectItem>
                      <SelectItem value="WR">WR</SelectItem>
                      <SelectItem value="TE">TE</SelectItem>
                      <SelectItem value="OL">OL</SelectItem>
                      <SelectItem value="DL">DL</SelectItem>
                      <SelectItem value="LB">LB</SelectItem>
                      <SelectItem value="CB">CB</SelectItem>
                      <SelectItem value="S">S</SelectItem>
                      <SelectItem value="K">K</SelectItem>
                      <SelectItem value="P">P</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </>
            )}

            {activeTab === 'coach' && (
              <>
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">Team</label>
                  <Select value={teamFilter} onValueChange={setTeamFilter}>
                    <SelectTrigger className="bg-[#1a2332] border-[#2d4a6f] text-white">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="NE">NE</SelectItem>
                      <SelectItem value="BUF">BUF</SelectItem>
                      <SelectItem value="MIA">MIA</SelectItem>
                      <SelectItem value="NYJ">NYJ</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="block text-xs text-[#94a3b8] mb-1">Role</label>
                  <Select value={roleFilter} onValueChange={setRoleFilter}>
                    <SelectTrigger className="bg-[#1a2332] border-[#2d4a6f] text-white">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="HC">HC</SelectItem>
                      <SelectItem value="OC">OC</SelectItem>
                      <SelectItem value="DC">DC</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </>
            )}

            {/* Search - Common to all tabs */}
            <div>
              <label className="block text-xs text-[#94a3b8] mb-1">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[#94a3b8]" />
                <Input
                  type="text"
                  placeholder={`Search ${activeTab} name...`}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-[#1a2332] border-[#2d4a6f] text-white placeholder:text-[#94a3b8]"
                />
              </div>
            </div>

            {/* Customize Stats Button */}
            <div>
              <Button
                onClick={() => setShowColumnChooser(true)}
                className="bg-[#2d4a6f] hover:bg-[#3d5a8f] text-white"
              >
                <Settings className="h-4 w-4 mr-2" />
                Customize Columns
              </Button>
            </div>

            {/* Export Button */}
            <div>
              <Button
                onClick={handleExport}
                variant="outline"
                className="bg-transparent border-[#d4af37] text-[#d4af37] hover:bg-[#d4af37]/10"
              >
                <Download className="h-4 w-4 mr-2" />
                Export to Sheets
              </Button>
            </div>
          </div>
        </div>

        {/* Top synced scrollbar */}
        <div className="roster-scrollbar" id="statsTopScrollbar" ref={topScrollbarRef}>
          <div className="sizer"></div>
        </div>

        {/* Scrollable table region */}
        <div className="roster-scroll" id="statsBodyScroll" ref={bodyScrollRef}>
          <table className="roster-table" id="statsTable" ref={tableRef}>
            <thead id="statsHead">
              <tr className="border-b border-[#2d4a6f]">
                {currentStats.map((stat, index) => (
                  <th
                    key={stat.id}
                    className={`px-4 py-3 text-left text-xs uppercase tracking-wide whitespace-nowrap ${
                      index === 0 ? 'stickyCol' : ''
                    }`}
                    title={stat.label}
                  >
                    <button
                      onClick={() => handleSort(stat.variable)}
                      className="flex items-center gap-1 text-white hover:text-[#d4af37] transition-colors w-full"
                    >
                      <span>{stat.variable}</span>
                      {sortColumn === stat.variable ? (
                        sortDirection === 'asc' ? (
                          <ArrowUp className="h-3 w-3 text-[#d4af37]" />
                        ) : (
                          <ArrowDown className="h-3 w-3 text-[#d4af37]" />
                        )
                      ) : (
                        <ArrowUpDown className="h-3 w-3 opacity-30" />
                      )}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#2d4a6f]">
              {currentData.length > 0 ? (
                currentData.map((item, rowIndex) => (
                  <tr key={item.id} className="group hover:bg-[#2d4a6f]/30">
                    {currentStats.map((stat, colIndex) => (
                      <td
                        key={stat.id}
                        className={`px-4 py-3 text-sm text-white whitespace-nowrap ${
                          colIndex === 0 ? 'stickyCol' : ''
                        }`}
                      >
                        {colIndex === 0 && activeTab === 'player' && stat.variable === 'player_name' ? (
                          <ClickablePlayerName player={item}>
                            {getValue(item, stat.variable)}
                          </ClickablePlayerName>
                        ) : colIndex === 0 && activeTab === 'coach' && stat.variable === 'coach_name' ? (
                          <ClickableCoachName coach={item}>
                            {getValue(item, stat.variable)}
                          </ClickableCoachName>
                        ) : (
                          getValue(item, stat.variable)
                        )}
                      </td>
                    ))}
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={currentStats.length} className="px-4 py-12 text-center text-[#94a3b8]">
                    No {activeTab}s found matching your filters
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Footer with count */}
        <div className="p-4 border-t border-[#2d4a6f] bg-[#0a1929]">
          <p className="text-sm text-[#94a3b8]">
            Showing {currentData.length} {activeTab}{currentData.length !== 1 ? 's' : ''} · {currentStats.length} column{currentStats.length !== 1 ? 's' : ''} displayed
          </p>
        </div>
      </div>

      {/* Stat Column Chooser Modal */}
      <StatColumnChooser
        open={showColumnChooser}
        onOpenChange={setShowColumnChooser}
        type={activeTab}
        categories={
          activeTab === 'player' ? playerStatCategories
            : activeTab === 'team' ? teamStatCategories
            : coachStatCategories
        }
        selectedStats={currentStats}
        onApply={handleApplyStats}
      />
    </div>
  );
}
