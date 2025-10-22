import { useState, useEffect } from 'react';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

interface PerformerStat {
  name: string;
  position: string;
  value: number;
  secondary?: string;
}

interface TeamData {
  passing: PerformerStat[];
  rushing: PerformerStat[];
  receiving: PerformerStat[];
  sacks: PerformerStat[];
  tackles: PerformerStat[];
  interceptions: PerformerStat[];
}

const NFL_TEAMS = [
  { id: 'NE', name: 'New England Patriots' },
  { id: 'BUF', name: 'Buffalo Bills' },
  { id: 'MIA', name: 'Miami Dolphins' },
  { id: 'NYJ', name: 'New York Jets' },
  { id: 'BAL', name: 'Baltimore Ravens' },
  { id: 'CIN', name: 'Cincinnati Bengals' },
  { id: 'CLE', name: 'Cleveland Browns' },
  { id: 'PIT', name: 'Pittsburgh Steelers' },
  { id: 'HOU', name: 'Houston Texans' },
  { id: 'IND', name: 'Indianapolis Colts' },
  { id: 'JAX', name: 'Jacksonville Jaguars' },
  { id: 'TEN', name: 'Tennessee Titans' },
  { id: 'DEN', name: 'Denver Broncos' },
  { id: 'KC', name: 'Kansas City Chiefs' },
  { id: 'LV', name: 'Las Vegas Raiders' },
  { id: 'LAC', name: 'Los Angeles Chargers' },
  { id: 'DAL', name: 'Dallas Cowboys' },
  { id: 'NYG', name: 'New York Giants' },
  { id: 'PHI', name: 'Philadelphia Eagles' },
  { id: 'WAS', name: 'Washington Commanders' },
  { id: 'CHI', name: 'Chicago Bears' },
  { id: 'DET', name: 'Detroit Lions' },
  { id: 'GB', name: 'Green Bay Packers' },
  { id: 'MIN', name: 'Minnesota Vikings' },
  { id: 'ATL', name: 'Atlanta Falcons' },
  { id: 'CAR', name: 'Carolina Panthers' },
  { id: 'NO', name: 'New Orleans Saints' },
  { id: 'TB', name: 'Tampa Bay Buccaneers' },
  { id: 'ARI', name: 'Arizona Cardinals' },
  { id: 'LAR', name: 'Los Angeles Rams' },
  { id: 'SF', name: 'San Francisco 49ers' },
  { id: 'SEA', name: 'Seattle Seahawks' },
];

const DEMO_DATA: Record<string, TeamData> = {
  'NE': {
    passing: [
      { name: "M. Jones", position: "QB", value: 3245, secondary: "18 TD" },
      { name: "B. Zappe", position: "QB", value: 567, secondary: "3 TD" },
    ],
    rushing: [
      { name: "R. Stevenson", position: "RB", value: 1124, secondary: "8 TD" },
      { name: "E. Elliott", position: "RB", value: 456, secondary: "3 TD" },
      { name: "M. Jones", position: "QB", value: 234, secondary: "2 TD" },
    ],
    receiving: [
      { name: "J. Meyers", position: "WR", value: 892, secondary: "6 TD" },
      { name: "D. Parker", position: "WR", value: 678, secondary: "4 TD" },
      { name: "K. Bourne", position: "WR", value: 534, secondary: "3 TD" },
    ],
    sacks: [
      { name: "M. Judon", position: "LB", value: 12.5, secondary: "42 TCK" },
      { name: "D. Godchaux", position: "DT", value: 6.0, secondary: "38 TCK" },
      { name: "J. Uche", position: "LB", value: 5.5, secondary: "31 TCK" },
    ],
    tackles: [
      { name: "J. Peppers", position: "S", value: 98, secondary: "2 INT" },
      { name: "K. Dugger", position: "S", value: 87, secondary: "3 INT" },
      { name: "M. Judon", position: "LB", value: 76, secondary: "12.5 SK" },
    ],
    interceptions: [
      { name: "K. Dugger", position: "S", value: 3, secondary: "87 TCK" },
      { name: "J. Peppers", position: "S", value: 2, secondary: "98 TCK" },
      { name: "J. Jones", position: "CB", value: 2, secondary: "54 TCK" },
    ],
  },
  'BUF': {
    passing: [
      { name: "J. Allen", position: "QB", value: 4127, secondary: "32 TD" },
      { name: "K. Dorsey", position: "QB", value: 89, secondary: "0 TD" },
    ],
    rushing: [
      { name: "J. Cook", position: "RB", value: 1456, secondary: "12 TD" },
      { name: "J. Allen", position: "QB", value: 612, secondary: "7 TD" },
      { name: "L. Murray", position: "RB", value: 287, secondary: "2 TD" },
    ],
    receiving: [
      { name: "S. Diggs", position: "WR", value: 1287, secondary: "11 TD" },
      { name: "G. Davis", position: "WR", value: 836, secondary: "7 TD" },
      { name: "D. Knox", position: "TE", value: 567, secondary: "5 TD" },
    ],
    sacks: [
      { name: "V. Miller", position: "LB", value: 14.0, secondary: "51 TCK" },
      { name: "G. Rousseau", position: "DE", value: 9.5, secondary: "47 TCK" },
      { name: "E. Oliver", position: "DT", value: 7.0, secondary: "44 TCK" },
    ],
    tackles: [
      { name: "T. Bernard", position: "LB", value: 112, secondary: "1 INT" },
      { name: "J. Poyer", position: "S", value: 95, secondary: "4 INT" },
      { name: "M. Hyde", position: "S", value: 89, secondary: "3 INT" },
    ],
    interceptions: [
      { name: "J. Poyer", position: "S", value: 4, secondary: "95 TCK" },
      { name: "M. Hyde", position: "S", value: 3, secondary: "89 TCK" },
      { name: "T. White", position: "CB", value: 3, secondary: "67 TCK" },
    ],
  },
  'MIA': {
    passing: [
      { name: "T. Tagovailoa", position: "QB", value: 3912, secondary: "28 TD" },
      { name: "T. Thompson", position: "QB", value: 234, secondary: "1 TD" },
    ],
    rushing: [
      { name: "R. Mostert", position: "RB", value: 978, secondary: "11 TD" },
      { name: "J. Wilson", position: "RB", value: 734, secondary: "5 TD" },
      { name: "D. Achane", position: "RB", value: 523, secondary: "4 TD" },
    ],
    receiving: [
      { name: "T. Hill", position: "WR", value: 1534, secondary: "13 TD" },
      { name: "J. Waddle", position: "WR", value: 1098, secondary: "8 TD" },
      { name: "D. Smythe", position: "TE", value: 445, secondary: "3 TD" },
    ],
    sacks: [
      { name: "B. Chubb", position: "LB", value: 11.0, secondary: "48 TCK" },
      { name: "J. Phillips", position: "DE", value: 8.5, secondary: "41 TCK" },
      { name: "C. Wilkins", position: "DT", value: 6.0, secondary: "52 TCK" },
    ],
    tackles: [
      { name: "J. Holland", position: "S", value: 104, secondary: "2 INT" },
      { name: "D. Long", position: "LB", value: 93, secondary: "1 INT" },
      { name: "B. Chubb", position: "LB", value: 76, secondary: "11.0 SK" },
    ],
    interceptions: [
      { name: "X. Howard", position: "CB", value: 5, secondary: "62 TCK" },
      { name: "J. Holland", position: "S", value: 2, secondary: "104 TCK" },
      { name: "K. Kohou", position: "CB", value: 2, secondary: "58 TCK" },
    ],
  },
  'KC': {
    passing: [
      { name: "P. Mahomes", position: "QB", value: 4234, secondary: "35 TD" },
      { name: "C. Wentz", position: "QB", value: 67, secondary: "0 TD" },
    ],
    rushing: [
      { name: "I. Pacheco", position: "RB", value: 1123, secondary: "9 TD" },
      { name: "P. Mahomes", position: "QB", value: 421, secondary: "4 TD" },
      { name: "J. McKinnon", position: "RB", value: 312, secondary: "2 TD" },
    ],
    receiving: [
      { name: "T. Kelce", position: "TE", value: 1198, secondary: "10 TD" },
      { name: "M. Valdes-Scantling", position: "WR", value: 723, secondary: "6 TD" },
      { name: "J. Smith-Schuster", position: "WR", value: 687, secondary: "5 TD" },
    ],
    sacks: [
      { name: "C. Jones", position: "DT", value: 13.5, secondary: "54 TCK" },
      { name: "G. Karlaftis", position: "DE", value: 9.0, secondary: "42 TCK" },
      { name: "F. Clark", position: "DE", value: 7.5, secondary: "38 TCK" },
    ],
    tackles: [
      { name: "N. Bolton", position: "LB", value: 118, secondary: "1 INT" },
      { name: "J. Reid", position: "S", value: 97, secondary: "3 INT" },
      { name: "L. Sneed", position: "CB", value: 84, secondary: "4 INT" },
    ],
    interceptions: [
      { name: "L. Sneed", position: "CB", value: 4, secondary: "84 TCK" },
      { name: "J. Reid", position: "S", value: 3, secondary: "97 TCK" },
      { name: "T. McDuffie", position: "CB", value: 2, secondary: "71 TCK" },
    ],
  },
};

// Generate basic demo data for teams not in DEMO_DATA
const generateTeamData = (teamId: string): TeamData => ({
  passing: [
    { name: `${teamId} QB1`, position: "QB", value: 3000 + Math.floor(Math.random() * 1500), secondary: `${15 + Math.floor(Math.random() * 20)} TD` },
    { name: `${teamId} QB2`, position: "QB", value: 200 + Math.floor(Math.random() * 500), secondary: `${1 + Math.floor(Math.random() * 5)} TD` },
  ],
  rushing: [
    { name: `${teamId} RB1`, position: "RB", value: 800 + Math.floor(Math.random() * 800), secondary: `${5 + Math.floor(Math.random() * 10)} TD` },
    { name: `${teamId} RB2`, position: "RB", value: 300 + Math.floor(Math.random() * 400), secondary: `${2 + Math.floor(Math.random() * 5)} TD` },
    { name: `${teamId} QB1`, position: "QB", value: 200 + Math.floor(Math.random() * 400), secondary: `${1 + Math.floor(Math.random() * 5)} TD` },
  ],
  receiving: [
    { name: `${teamId} WR1`, position: "WR", value: 900 + Math.floor(Math.random() * 700), secondary: `${6 + Math.floor(Math.random() * 8)} TD` },
    { name: `${teamId} WR2`, position: "WR", value: 600 + Math.floor(Math.random() * 500), secondary: `${4 + Math.floor(Math.random() * 6)} TD` },
    { name: `${teamId} TE1`, position: "TE", value: 400 + Math.floor(Math.random() * 400), secondary: `${3 + Math.floor(Math.random() * 5)} TD` },
  ],
  sacks: [
    { name: `${teamId} DE1`, position: "DE", value: 8 + Math.floor(Math.random() * 8), secondary: `${35 + Math.floor(Math.random() * 20)} TCK` },
    { name: `${teamId} LB1`, position: "LB", value: 6 + Math.floor(Math.random() * 6), secondary: `${40 + Math.floor(Math.random() * 20)} TCK` },
    { name: `${teamId} DT1`, position: "DT", value: 4 + Math.floor(Math.random() * 5), secondary: `${30 + Math.floor(Math.random() * 20)} TCK` },
  ],
  tackles: [
    { name: `${teamId} LB1`, position: "LB", value: 90 + Math.floor(Math.random() * 30), secondary: `${1 + Math.floor(Math.random() * 3)} INT` },
    { name: `${teamId} S1`, position: "S", value: 80 + Math.floor(Math.random() * 25), secondary: `${2 + Math.floor(Math.random() * 4)} INT` },
    { name: `${teamId} LB2`, position: "LB", value: 70 + Math.floor(Math.random() * 25), secondary: `${1 + Math.floor(Math.random() * 2)} INT` },
  ],
  interceptions: [
    { name: `${teamId} CB1`, position: "CB", value: 3 + Math.floor(Math.random() * 3), secondary: `${60 + Math.floor(Math.random() * 25)} TCK` },
    { name: `${teamId} S1`, position: "S", value: 2 + Math.floor(Math.random() * 3), secondary: `${70 + Math.floor(Math.random() * 30)} TCK` },
    { name: `${teamId} CB2`, position: "CB", value: 2 + Math.floor(Math.random() * 2), secondary: `${55 + Math.floor(Math.random() * 20)} TCK` },
  ],
});

export function TeamTopPerformers() {
  const [selectedTeam, setSelectedTeam] = useState('NE');
  const [data, setData] = useState<TeamData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [sortBy, setSortBy] = useState<'passing' | 'rushing' | 'receiving' | 'sacks' | 'tackles' | 'interceptions'>('passing');

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => {
      const teamData = DEMO_DATA[selectedTeam] || generateTeamData(selectedTeam);
      setData(teamData);
      setLoading(false);
    }, 400);

    return () => clearTimeout(timer);
  }, [selectedTeam]);

  const sortOptions = [
    { value: 'passing', label: 'Passing Yards' },
    { value: 'rushing', label: 'Rushing Yards' },
    { value: 'receiving', label: 'Receiving Yards' },
    { value: 'sacks', label: 'Sacks' },
    { value: 'tackles', label: 'Tackles' },
    { value: 'interceptions', label: 'Interceptions' },
  ];

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f]">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-white">Team Top Performers</h3>
        </div>
        
        {/* Team Selector */}
        <div className="mb-3">
          <Select value={selectedTeam} onValueChange={setSelectedTeam}>
            <SelectTrigger className="w-full bg-[#0a1929] border-[#2d4a6f] text-white">
              <SelectValue placeholder="Select team" />
            </SelectTrigger>
            <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-h-[300px]">
              {NFL_TEAMS.map((team) => (
                <SelectItem 
                  key={team.id} 
                  value={team.id}
                  className="text-white hover:bg-[#2d4a6f] focus:bg-[#2d4a6f] focus:text-white"
                >
                  {team.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Sort Selector */}
        <div className="flex gap-2">
          <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
            <SelectTrigger className="flex-1 bg-[#0a1929] border-[#2d4a6f] text-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
              {sortOptions.map((option) => (
                <SelectItem 
                  key={option.value} 
                  value={option.value}
                  className="text-white hover:bg-[#2d4a6f] focus:bg-[#2d4a6f] focus:text-white"
                >
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        <p className="text-[#94a3b8] text-xs mt-2">(demo)</p>
      </div>

      {error && (
        <div className="p-4">
          <Alert className="bg-[#991b1b]/20 border-[#dc2626] text-white">
            <AlertDescription className="text-sm">
              Couldn't load team performers. Showing demo.
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Content */}
      <div className="p-4">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-10 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-10 w-full bg-[#2d4a6f]" />
          </div>
        ) : data ? (
          <div className="space-y-3">
            {data[sortBy].map((performer, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between py-2.5 px-3 bg-[#0a1929] rounded hover:bg-[#2d4a6f]/30 transition-colors min-h-[44px]"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-white">{performer.name}</div>
                  <div className="text-[#94a3b8] text-xs">{performer.position}</div>
                </div>
                <div className="text-right">
                  <div className="text-[#d4af37]">
                    {sortBy === 'sacks' ? performer.value.toFixed(1) : performer.value.toLocaleString()}
                  </div>
                  {performer.secondary && (
                    <div className="text-[#94a3b8] text-xs">{performer.secondary}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[#94a3b8] text-center py-8">No data available.</p>
        )}
      </div>
    </div>
  );
}
