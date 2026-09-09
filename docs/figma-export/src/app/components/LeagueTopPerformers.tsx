import { useState, useEffect } from 'react';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { ClickablePlayerName } from './ui/ClickablePlayerName';

interface TopPerformer {
  rank: number;
  player_name: string;
  team_id: string;
  position: string;
  value: number;
  stat_label: string;
}

const DEMO_DATA: Record<string, TopPerformer[]> = {
  'qb-rating': [
    { rank: 1, player_name: "P. Mahomes", team_id: "KC", position: "QB", value: 108.2, stat_label: "QB Rating" },
    { rank: 2, player_name: "J. Allen", team_id: "BUF", position: "QB", value: 104.7, stat_label: "QB Rating" },
    { rank: 3, player_name: "B. Purdy", team_id: "SF", position: "QB", value: 102.1, stat_label: "QB Rating" },
    { rank: 4, player_name: "J. Hurts", team_id: "PHI", position: "QB", value: 99.8, stat_label: "QB Rating" },
    { rank: 5, player_name: "D. Prescott", team_id: "DAL", position: "QB", value: 98.3, stat_label: "QB Rating" },
  ],
  'passing-yards': [
    { rank: 1, player_name: "P. Mahomes", team_id: "KC", position: "QB", value: 4183, stat_label: "Pass Yds" },
    { rank: 2, player_name: "J. Goff", team_id: "DET", position: "QB", value: 4025, stat_label: "Pass Yds" },
    { rank: 3, player_name: "T. Tagovailoa", team_id: "MIA", position: "QB", value: 3978, stat_label: "Pass Yds" },
    { rank: 4, player_name: "J. Allen", team_id: "BUF", position: "QB", value: 3891, stat_label: "Pass Yds" },
    { rank: 5, player_name: "D. Prescott", team_id: "DAL", position: "QB", value: 3845, stat_label: "Pass Yds" },
  ],
  'passing-tds': [
    { rank: 1, player_name: "P. Mahomes", team_id: "KC", position: "QB", value: 38, stat_label: "Pass TD" },
    { rank: 2, player_name: "J. Hurts", team_id: "PHI", position: "QB", value: 34, stat_label: "Pass TD" },
    { rank: 3, player_name: "D. Prescott", team_id: "DAL", position: "QB", value: 32, stat_label: "Pass TD" },
    { rank: 4, player_name: "J. Allen", team_id: "BUF", position: "QB", value: 31, stat_label: "Pass TD" },
    { rank: 5, player_name: "B. Purdy", team_id: "SF", position: "QB", value: 29, stat_label: "Pass TD" },
  ],
  'interceptions': [
    { rank: 1, player_name: "T. Diggs", team_id: "DAL", position: "CB", value: 7, stat_label: "INT" },
    { rank: 2, player_name: "J. Ramsey", team_id: "MIA", position: "CB", value: 6, stat_label: "INT" },
    { rank: 3, player_name: "X. McKinney", team_id: "GB", position: "S", value: 6, stat_label: "INT" },
    { rank: 4, player_name: "C.J. Gardner-Johnson", team_id: "PHI", position: "S", value: 5, stat_label: "INT" },
    { rank: 5, player_name: "D. James", team_id: "LAC", position: "S", value: 5, stat_label: "INT" },
  ],
  'rushing-yards': [
    { rank: 1, player_name: "C. McCaffrey", team_id: "SF", position: "RB", value: 1459, stat_label: "Rush Yds" },
    { rank: 2, player_name: "R. Mostert", team_id: "MIA", position: "RB", value: 1198, stat_label: "Rush Yds" },
    { rank: 3, player_name: "D. Cook", team_id: "NYJ", position: "RB", value: 1147, stat_label: "Rush Yds" },
    { rank: 4, player_name: "K. Williams", team_id: "LAR", position: "RB", value: 1092, stat_label: "Rush Yds" },
    { rank: 5, player_name: "B. Hall", team_id: "NYJ", position: "RB", value: 1045, stat_label: "Rush Yds" },
  ],
  'rushing-tds': [
    { rank: 1, player_name: "C. McCaffrey", team_id: "SF", position: "RB", value: 14, stat_label: "Rush TD" },
    { rank: 2, player_name: "J. Taylor", team_id: "IND", position: "RB", value: 11, stat_label: "Rush TD" },
    { rank: 3, player_name: "D. Henry", team_id: "TEN", position: "RB", value: 10, stat_label: "Rush TD" },
    { rank: 4, player_name: "R. Mostert", team_id: "MIA", position: "RB", value: 9, stat_label: "Rush TD" },
    { rank: 5, player_name: "J. Mixon", team_id: "CIN", position: "RB", value: 9, stat_label: "Rush TD" },
  ],
  'receiving-yards': [
    { rank: 1, player_name: "T. Hill", team_id: "MIA", position: "WR", value: 1542, stat_label: "Rec Yds" },
    { rank: 2, player_name: "C. Lamb", team_id: "DAL", position: "WR", value: 1489, stat_label: "Rec Yds" },
    { rank: 3, player_name: "A. St. Brown", team_id: "DET", position: "WR", value: 1432, stat_label: "Rec Yds" },
    { rank: 4, player_name: "D. Adams", team_id: "LV", position: "WR", value: 1387, stat_label: "Rec Yds" },
    { rank: 5, player_name: "S. Diggs", team_id: "BUF", position: "WR", value: 1321, stat_label: "Rec Yds" },
  ],
  'receiving-tds': [
    { rank: 1, player_name: "T. Hill", team_id: "MIA", position: "WR", value: 13, stat_label: "Rec TD" },
    { rank: 2, player_name: "C. Lamb", team_id: "DAL", position: "WR", value: 12, stat_label: "Rec TD" },
    { rank: 3, player_name: "D. Adams", team_id: "LV", position: "WR", value: 11, stat_label: "Rec TD" },
    { rank: 4, player_name: "A.J. Brown", team_id: "PHI", position: "WR", value: 10, stat_label: "Rec TD" },
    { rank: 5, player_name: "M. Evans", team_id: "TB", position: "WR", value: 10, stat_label: "Rec TD" },
  ],
  'sacks': [
    { rank: 1, player_name: "M. Crosby", team_id: "LV", position: "DE", value: 14.5, stat_label: "Sacks" },
    { rank: 2, player_name: "T.J. Watt", team_id: "PIT", position: "LB", value: 13.0, stat_label: "Sacks" },
    { rank: 3, player_name: "M. Parsons", team_id: "DAL", position: "LB", value: 12.5, stat_label: "Sacks" },
    { rank: 4, player_name: "N. Bosa", team_id: "SF", position: "DE", value: 12.0, stat_label: "Sacks" },
    { rank: 5, player_name: "M. Judon", team_id: "NE", position: "LB", value: 11.5, stat_label: "Sacks" },
  ],
  'tackles': [
    { rank: 1, player_name: "B. Wagner", team_id: "SEA", position: "LB", value: 142, stat_label: "Tackles" },
    { rank: 2, player_name: "F. Warner", team_id: "SF", position: "LB", value: 135, stat_label: "Tackles" },
    { rank: 3, player_name: "R. Leonard", team_id: "IND", position: "LB", value: 128, stat_label: "Tackles" },
    { rank: 4, player_name: "D. Campbell", team_id: "GB", position: "LB", value: 124, stat_label: "Tackles" },
    { rank: 5, player_name: "Z. Cunningham", team_id: "TEN", position: "LB", value: 119, stat_label: "Tackles" },
  ],
};

export function LeagueTopPerformers() {
  const [data, setData] = useState<TopPerformer[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [category, setCategory] = useState('qb-rating');
  const [conference, setConference] = useState('all');

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => {
      setData(DEMO_DATA[category] || []);
      setLoading(false);
    }, 600);

    return () => clearTimeout(timer);
  }, [category]);

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f]">
        <h3 className="text-white mb-3">League Top Performers</h3>
        <div className="flex gap-2 mb-2">
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger className="flex-1 bg-[#0a1929] border-[#2d4a6f] text-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
              <SelectItem value="qb-rating">QB Rating</SelectItem>
              <SelectItem value="passing-yards">Passing Yards</SelectItem>
              <SelectItem value="passing-tds">Passing TDs</SelectItem>
              <SelectItem value="rushing-yards">Rushing Yards</SelectItem>
              <SelectItem value="rushing-tds">Rushing TDs</SelectItem>
              <SelectItem value="receiving-yards">Receiving Yards</SelectItem>
              <SelectItem value="receiving-tds">Receiving TDs</SelectItem>
              <SelectItem value="sacks">Sacks</SelectItem>
              <SelectItem value="tackles">Tackles</SelectItem>
              <SelectItem value="interceptions">Interceptions</SelectItem>
            </SelectContent>
          </Select>
          <Select value={conference} onValueChange={setConference}>
            <SelectTrigger className="w-24 bg-[#0a1929] border-[#2d4a6f] text-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="afc">AFC</SelectItem>
              <SelectItem value="nfc">NFC</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <p className="text-[#94a3b8] text-xs">(demo)</p>
      </div>

      {error && (
        <div className="px-4 pt-3">
          <Alert className="bg-[#991b1b]/20 border-[#dc2626] text-white">
            <AlertDescription className="text-sm">
              Couldn't load performers. Showing demo.
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Content */}
      <div className="p-4">
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-12 w-full bg-[#2d4a6f]" />
            ))}
          </div>
        ) : data && data.length > 0 ? (
          <div className="space-y-1">
            {data.map((player) => (
              <div
                key={player.rank}
                className="flex items-center justify-between py-3 px-3 hover:bg-[#2d4a6f]/30 rounded transition-colors min-h-[44px]"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <span className="text-[#d4af37] text-sm w-6 flex-shrink-0">{player.rank}</span>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm truncate">
                      <ClickablePlayerName 
                        player={{ name: player.player_name, pos: player.position, ovr: 85, age: 27 }}
                        className="text-white"
                      />
                    </div>
                    <div className="text-[#94a3b8] text-xs">
                      {player.team_id} · {player.position}
                    </div>
                  </div>
                </div>
                <div className="text-white text-sm ml-3 flex-shrink-0">
                  {player.value.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[#94a3b8] text-center py-8">No performer data available.</p>
        )}
      </div>
    </div>
  );
}
