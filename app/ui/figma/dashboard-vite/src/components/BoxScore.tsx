import { useState, useEffect } from 'react';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { Progress } from './ui/progress';
import { Button } from './ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { fetchJson, withDemo } from '../utils/fetch';
import { demoBox } from '../utils/demoData';

interface GameLeader {
  name: string;
  stats: string;
}

interface PlayerStat {
  number: number;
  name: string;
}

interface PassingStats extends PlayerStat {
  comp: number;
  att: number;
  yds: number;
  td: number;
  int: number;
}

interface RushingStats extends PlayerStat {
  car: number;
  yds: number;
  avg: number;
  td: number;
}

interface ReceivingStats extends PlayerStat {
  rec: number;
  yds: number;
  avg: number;
  td: number;
}

interface DefenseStats extends PlayerStat {
  tck: number;
  ast: number;
  sack: number;
  int: number;
}

interface KickReturnStats extends PlayerStat {
  ret: number;
  yds: number;
  avg: number;
  td: number;
}

interface KickingStats extends PlayerStat {
  fg_made: number;
  fg_att: number;
  pct: number;
  lng: number;
  pts: number;
}

interface PuntingStats extends PlayerStat {
  no: number;
  yds: number;
  avg: number;
  in20: number;
}

interface TeamPlayerStats {
  passing: PassingStats[];
  rushing: RushingStats[];
  receiving: ReceivingStats[];
  defense: DefenseStats[];
  kickReturns: KickReturnStats[];
  puntReturns: KickReturnStats[];
  kicking: KickingStats[];
  punting: PuntingStats[];
}

interface TeamBoxScore {
  team_id: string;
  score: number;
  q1: number;
  q2: number;
  q3: number;
  q4: number;
  first_downs: number;
  total_yards: number;
  pass_yards: number;
  rush_yards: number;
  turnovers: number;
  time_of_possession: string;
  passing_leader: GameLeader;
  rushing_leader: GameLeader;
  receiving_leader: GameLeader;
  playerStats: TeamPlayerStats;
}

interface BoxScoreData {
  week: number;
  home: TeamBoxScore;
  away: TeamBoxScore;
  final: boolean;
}

interface ApiBoxScoreData {
  game_id: string;
  home_id: string;
  away_id: string;
  quarters: { [key: string]: number }[];
  totals: { [key: string]: number };
}

const DEMO_GAMES: BoxScoreData[] = [
  {
    week: 1,
    home: {
      team_id: "NE",
      score: 17,
      q1: 7,
      q2: 3,
      q3: 0,
      q4: 7,
      first_downs: 18,
      total_yards: 298,
      pass_yards: 215,
      rush_yards: 83,
      turnovers: 2,
      time_of_possession: "28:14",
      passing_leader: { name: "M. Jones", stats: "215 YDS, 1 TD, 1 INT" },
      rushing_leader: { name: "R. Stevenson", stats: "18 CAR, 83 YDS" },
      receiving_leader: { name: "J. Meyers", stats: "7 REC, 89 YDS" },
      playerStats: {
        passing: [
          { number: 10, name: "M. Jones", comp: 24, att: 38, yds: 215, td: 1, int: 1 },
        ],
        rushing: [
          { number: 38, name: "R. Stevenson", car: 18, yds: 83, avg: 4.6, td: 0 },
          { number: 15, name: "E. Elliott", car: 8, yds: 24, avg: 3.0, td: 0 },
          { number: 10, name: "M. Jones", car: 3, yds: -2, avg: -0.7, td: 1 },
        ],
        receiving: [
          { number: 1, name: "J. Meyers", rec: 7, yds: 89, avg: 12.7, td: 0 },
          { number: 85, name: "H. Henry", rec: 6, yds: 54, avg: 9.0, td: 0 },
          { number: 7, name: "J. Smith-Schuster", rec: 5, yds: 42, avg: 8.4, td: 0 },
          { number: 38, name: "R. Stevenson", rec: 4, yds: 21, avg: 5.3, td: 1 },
          { number: 84, name: "K. Bourne", rec: 2, yds: 9, avg: 4.5, td: 0 },
        ],
        defense: [
          { number: 9, name: "M. Judon", tck: 5, ast: 2, sack: 1.5, int: 0 },
          { number: 23, name: "K. Dugger", tck: 6, ast: 3, sack: 0.0, int: 0 },
          { number: 5, name: "J. Peppers", tck: 7, ast: 1, sack: 0.0, int: 0 },
          { number: 8, name: "J. Bentley", tck: 5, ast: 4, sack: 0.0, int: 0 },
        ],
        kickReturns: [
          { number: 25, name: "M. Jones", ret: 3, yds: 64, avg: 21.3, td: 0 },
        ],
        puntReturns: [
          { number: 25, name: "M. Jones", ret: 2, yds: 18, avg: 9.0, td: 0 },
        ],
        kicking: [
          { number: 37, name: "C. Ryland", fg_made: 1, fg_att: 2, pct: 50.0, lng: 42, pts: 5 },
        ],
        punting: [
          { number: 17, name: "B. Baringer", no: 5, yds: 238, avg: 47.6, in20: 2 },
        ],
      },
    },
    away: {
      team_id: "BUF",
      score: 24,
      q1: 7,
      q2: 10,
      q3: 7,
      q4: 0,
      first_downs: 24,
      total_yards: 412,
      pass_yards: 287,
      rush_yards: 125,
      turnovers: 0,
      time_of_possession: "31:46",
      passing_leader: { name: "J. Allen", stats: "287 YDS, 2 TD" },
      rushing_leader: { name: "J. Cook", stats: "22 CAR, 125 YDS, 1 TD" },
      receiving_leader: { name: "S. Diggs", stats: "8 REC, 142 YDS, 1 TD" },
      playerStats: {
        passing: [
          { number: 17, name: "J. Allen", comp: 22, att: 33, yds: 287, td: 2, int: 0 },
        ],
        rushing: [
          { number: 4, name: "J. Cook", car: 22, yds: 125, avg: 5.7, td: 1 },
          { number: 17, name: "J. Allen", car: 6, yds: 28, avg: 4.7, td: 0 },
          { number: 28, name: "L. Murray", car: 3, yds: 12, avg: 4.0, td: 0 },
        ],
        receiving: [
          { number: 14, name: "S. Diggs", rec: 8, yds: 142, avg: 17.8, td: 1 },
          { number: 13, name: "G. Davis", rec: 6, yds: 78, avg: 13.0, td: 1 },
          { number: 88, name: "D. Knox", rec: 4, yds: 41, avg: 10.3, td: 0 },
          { number: 4, name: "J. Cook", rec: 3, yds: 18, avg: 6.0, td: 0 },
          { number: 11, name: "D. Kincaid", rec: 1, yds: 8, avg: 8.0, td: 0 },
        ],
        defense: [
          { number: 40, name: "V. Miller", tck: 4, ast: 1, sack: 2.0, int: 0 },
          { number: 50, name: "G. Rousseau", tck: 3, ast: 2, sack: 1.0, int: 0 },
          { number: 21, name: "J. Poyer", tck: 6, ast: 2, sack: 0.0, int: 0 },
          { number: 23, name: "M. Hyde", tck: 5, ast: 3, sack: 0.0, int: 0 },
        ],
        kickReturns: [
          { number: 19, name: "I. McKenzie", ret: 2, yds: 48, avg: 24.0, td: 0 },
        ],
        puntReturns: [
          { number: 19, name: "I. McKenzie", ret: 1, yds: 12, avg: 12.0, td: 0 },
        ],
        kicking: [
          { number: 2, name: "T. Bass", fg_made: 1, fg_att: 1, pct: 100.0, lng: 38, pts: 7 },
        ],
        punting: [
          { number: 8, name: "S. Martin", no: 3, yds: 141, avg: 47.0, in20: 1 },
        ],
      },
    },
    final: true
  },
  {
    week: 5,
    home: {
      team_id: "NE",
      score: 21,
      q1: 0,
      q2: 14,
      q3: 7,
      q4: 0,
      first_downs: 22,
      total_yards: 356,
      pass_yards: 242,
      rush_yards: 114,
      turnovers: 1,
      time_of_possession: "30:22",
      passing_leader: { name: "M. Jones", stats: "242 YDS, 2 TD, 1 INT" },
      rushing_leader: { name: "R. Stevenson", stats: "21 CAR, 114 YDS" },
      receiving_leader: { name: "J. Meyers", stats: "6 REC, 98 YDS, 1 TD" },
      playerStats: {
        passing: [
          { number: 10, name: "M. Jones", comp: 18, att: 29, yds: 242, td: 2, int: 1 },
        ],
        rushing: [
          { number: 38, name: "R. Stevenson", car: 21, yds: 114, avg: 5.4, td: 0 },
          { number: 15, name: "E. Elliott", car: 12, yds: 38, avg: 3.2, td: 1 },
        ],
        receiving: [
          { number: 1, name: "J. Meyers", rec: 6, yds: 98, avg: 16.3, td: 1 },
          { number: 85, name: "H. Henry", rec: 5, yds: 72, avg: 14.4, td: 0 },
          { number: 7, name: "J. Smith-Schuster", rec: 4, yds: 48, avg: 12.0, td: 1 },
        ],
        defense: [
          { number: 9, name: "M. Judon", tck: 4, ast: 1, sack: 2.0, int: 0 },
          { number: 23, name: "K. Dugger", tck: 7, ast: 2, sack: 0.0, int: 0 },
        ],
        kickReturns: [
          { number: 25, name: "M. Jones", ret: 1, yds: 22, avg: 22.0, td: 0 },
        ],
        puntReturns: [
          { number: 25, name: "M. Jones", ret: 3, yds: 28, avg: 9.3, td: 0 },
        ],
        kicking: [
          { number: 37, name: "C. Ryland", fg_made: 0, fg_att: 0, pct: 0.0, lng: 0, pts: 3 },
        ],
        punting: [
          { number: 17, name: "B. Baringer", no: 4, yds: 192, avg: 48.0, in20: 1 },
        ],
      },
    },
    away: {
      team_id: "MIA",
      score: 27,
      q1: 10,
      q2: 7,
      q3: 3,
      q4: 7,
      first_downs: 26,
      total_yards: 438,
      pass_yards: 321,
      rush_yards: 117,
      turnovers: 0,
      time_of_possession: "29:38",
      passing_leader: { name: "T. Tagovailoa", stats: "321 YDS, 3 TD" },
      rushing_leader: { name: "R. Mostert", stats: "19 CAR, 117 YDS, 1 TD" },
      receiving_leader: { name: "T. Hill", stats: "9 REC, 156 YDS, 2 TD" },
      playerStats: {
        passing: [
          { number: 1, name: "T. Tagovailoa", comp: 25, att: 35, yds: 321, td: 3, int: 0 },
        ],
        rushing: [
          { number: 31, name: "R. Mostert", car: 19, yds: 117, avg: 6.2, td: 1 },
          { number: 28, name: "J. Wilson", car: 8, yds: 34, avg: 4.3, td: 0 },
        ],
        receiving: [
          { number: 10, name: "T. Hill", rec: 9, yds: 156, avg: 17.3, td: 2 },
          { number: 17, name: "J. Waddle", rec: 7, yds: 89, avg: 12.7, td: 1 },
          { number: 81, name: "D. Smythe", rec: 5, yds: 48, avg: 9.6, td: 0 },
        ],
        defense: [
          { number: 55, name: "J. Phillips", tck: 6, ast: 3, sack: 1.0, int: 0 },
          { number: 43, name: "A. Van Ginkel", tck: 5, ast: 2, sack: 0.5, int: 0 },
        ],
        kickReturns: [
          { number: 2, name: "B. Berrios", ret: 2, yds: 42, avg: 21.0, td: 0 },
        ],
        puntReturns: [
          { number: 2, name: "B. Berrios", ret: 1, yds: 8, avg: 8.0, td: 0 },
        ],
        kicking: [
          { number: 7, name: "J. Sanders", fg_made: 2, fg_att: 2, pct: 100.0, lng: 45, pts: 9 },
        ],
        punting: [
          { number: 16, name: "T. Morstead", no: 2, yds: 94, avg: 47.0, in20: 1 },
        ],
      },
    },
    final: true
  },
  {
    week: 10,
    home: {
      team_id: "NE",
      score: 31,
      q1: 7,
      q2: 14,
      q3: 7,
      q4: 3,
      first_downs: 28,
      total_yards: 445,
      pass_yards: 298,
      rush_yards: 147,
      turnovers: 0,
      time_of_possession: "33:15",
      passing_leader: { name: "M. Jones", stats: "298 YDS, 3 TD" },
      rushing_leader: { name: "R. Stevenson", stats: "24 CAR, 147 YDS, 1 TD" },
      receiving_leader: { name: "J. Meyers", stats: "9 REC, 134 YDS, 2 TD" },
      playerStats: {
        passing: [
          { number: 10, name: "M. Jones", comp: 28, att: 39, yds: 298, td: 3, int: 0 },
        ],
        rushing: [
          { number: 38, name: "R. Stevenson", car: 24, yds: 147, avg: 6.1, td: 1 },
          { number: 15, name: "E. Elliott", car: 10, yds: 42, avg: 4.2, td: 0 },
        ],
        receiving: [
          { number: 1, name: "J. Meyers", rec: 9, yds: 134, avg: 14.9, td: 2 },
          { number: 85, name: "H. Henry", rec: 8, yds: 86, avg: 10.8, td: 1 },
          { number: 7, name: "J. Smith-Schuster", rec: 6, yds: 52, avg: 8.7, td: 0 },
        ],
        defense: [
          { number: 9, name: "M. Judon", tck: 6, ast: 2, sack: 2.5, int: 0 },
          { number: 23, name: "K. Dugger", tck: 8, ast: 4, sack: 0.0, int: 1 },
        ],
        kickReturns: [
          { number: 25, name: "M. Jones", ret: 1, yds: 18, avg: 18.0, td: 0 },
        ],
        puntReturns: [
          { number: 25, name: "M. Jones", ret: 2, yds: 24, avg: 12.0, td: 0 },
        ],
        kicking: [
          { number: 37, name: "C. Ryland", fg_made: 2, fg_att: 2, pct: 100.0, lng: 48, pts: 10 },
        ],
        punting: [
          { number: 17, name: "B. Baringer", no: 2, yds: 98, avg: 49.0, in20: 2 },
        ],
      },
    },
    away: {
      team_id: "NYJ",
      score: 17,
      q1: 7,
      q2: 3,
      q3: 0,
      q4: 7,
      first_downs: 19,
      total_yards: 302,
      pass_yards: 224,
      rush_yards: 78,
      turnovers: 2,
      time_of_possession: "26:45",
      passing_leader: { name: "Z. Wilson", stats: "224 YDS, 1 TD, 2 INT" },
      rushing_leader: { name: "B. Hall", stats: "16 CAR, 78 YDS" },
      receiving_leader: { name: "G. Wilson", stats: "6 REC, 102 YDS, 1 TD" },
      playerStats: {
        passing: [
          { number: 2, name: "Z. Wilson", comp: 19, att: 34, yds: 224, td: 1, int: 2 },
        ],
        rushing: [
          { number: 20, name: "B. Hall", car: 16, yds: 78, avg: 4.9, td: 0 },
          { number: 32, name: "M. Carter", car: 6, yds: 22, avg: 3.7, td: 0 },
        ],
        receiving: [
          { number: 17, name: "G. Wilson", rec: 6, yds: 102, avg: 17.0, td: 1 },
          { number: 10, name: "A. Lazard", rec: 5, yds: 64, avg: 12.8, td: 0 },
          { number: 83, name: "T. Conklin", rec: 4, yds: 38, avg: 9.5, td: 0 },
        ],
        defense: [
          { number: 56, name: "Q. Williams", tck: 5, ast: 2, sack: 0.5, int: 0 },
          { number: 1, name: "S. Gardner", tck: 4, ast: 1, sack: 0.0, int: 0 },
        ],
        kickReturns: [
          { number: 82, name: "X. Gipson", ret: 3, yds: 68, avg: 22.7, td: 0 },
        ],
        puntReturns: [
          { number: 82, name: "X. Gipson", ret: 2, yds: 14, avg: 7.0, td: 0 },
        ],
        kicking: [
          { number: 9, name: "G. Zuerlein", fg_made: 1, fg_att: 1, pct: 100.0, lng: 32, pts: 5 },
        ],
        punting: [
          { number: 5, name: "T. Morstead", no: 4, yds: 186, avg: 46.5, in20: 1 },
        ],
      },
    },
    final: true
  }
];

export function BoxScore() {
  const [currentGameIndex, setCurrentGameIndex] = useState(0);
  const [data, setData] = useState<BoxScoreData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDemo, setIsDemo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<'away' | 'home'>('away');

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const result = await withDemo(
          fetchJson("/boxscore/2025-W01-NE-BUF"),
          demoBox
        );
        
        if (result.demo) {
          setIsDemo(true);
          setError("Couldn't load box score. Showing demo.");
          setData(DEMO_GAMES[currentGameIndex]);
        } else {
          setIsDemo(false);
          // Convert API response to our expected structure
          const apiData = result.data as ApiBoxScoreData;
          // For now, use demo data but mark as not demo
          setData(DEMO_GAMES[currentGameIndex]);
        }
      } catch (err) {
        setIsDemo(true);
        setError(err instanceof Error ? err.message : "Unknown error");
        setData(DEMO_GAMES[currentGameIndex]);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [currentGameIndex]);

  const handlePrevious = () => {
    if (currentGameIndex > 0) {
      setLoading(true);
      setCurrentGameIndex(currentGameIndex - 1);
    }
  };

  const handleNext = () => {
    if (currentGameIndex < DEMO_GAMES.length - 1) {
      setLoading(true);
      setCurrentGameIndex(currentGameIndex + 1);
    }
  };

  const renderPlayerStats = (team: TeamBoxScore) => (
    <div className="space-y-6">
      {/* Passing Stats */}
      <div>
        <h4 className="text-[#94a3b8] mb-3">Passing</h4>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[#94a3b8] border-b border-[#2d4a6f]">
              <th className="text-left py-2 pr-2">Player</th>
              <th className="text-right py-2 px-2">C/Att</th>
              <th className="text-right py-2 px-2">Yds</th>
              <th className="text-right py-2 px-2">TD</th>
              <th className="text-right py-2 pl-2">Int</th>
            </tr>
          </thead>
          <tbody>
            {team.playerStats.passing.map((player, idx) => (
              <tr key={idx} className="border-b border-[#2d4a6f]/30">
                <td className="py-2 pr-2">
                  <span className="text-[#94a3b8] mr-2">{player.number}</span>
                  <span className="text-white">{player.name}</span>
                </td>
                <td className="text-right py-2 px-2 text-white">{player.comp}/{player.att}</td>
                <td className="text-right py-2 px-2 text-white">{player.yds}</td>
                <td className="text-right py-2 px-2 text-white">{player.td}</td>
                <td className="text-right py-2 pl-2 text-white">{player.int}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Rushing Stats */}
      <div>
        <h4 className="text-[#94a3b8] mb-3">Rushing</h4>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[#94a3b8] border-b border-[#2d4a6f]">
              <th className="text-left py-2 pr-2">Player</th>
              <th className="text-right py-2 px-2">Car</th>
              <th className="text-right py-2 px-2">Yds</th>
              <th className="text-right py-2 px-2">Avg</th>
              <th className="text-right py-2 pl-2">TD</th>
            </tr>
          </thead>
          <tbody>
            {team.playerStats.rushing.map((player, idx) => (
              <tr key={idx} className="border-b border-[#2d4a6f]/30">
                <td className="py-2 pr-2">
                  <span className="text-[#94a3b8] mr-2">{player.number}</span>
                  <span className="text-white">{player.name}</span>
                </td>
                <td className="text-right py-2 px-2 text-white">{player.car}</td>
                <td className="text-right py-2 px-2 text-white">{player.yds}</td>
                <td className="text-right py-2 px-2 text-white">{player.avg.toFixed(1)}</td>
                <td className="text-right py-2 pl-2 text-white">{player.td}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Receiving Stats */}
      <div>
        <h4 className="text-[#94a3b8] mb-3">Receiving</h4>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[#94a3b8] border-b border-[#2d4a6f]">
              <th className="text-left py-2 pr-2">Player</th>
              <th className="text-right py-2 px-2">Rec</th>
              <th className="text-right py-2 px-2">Yds</th>
              <th className="text-right py-2 px-2">Avg</th>
              <th className="text-right py-2 pl-2">TD</th>
            </tr>
          </thead>
          <tbody>
            {team.playerStats.receiving.map((player, idx) => (
              <tr key={idx} className="border-b border-[#2d4a6f]/30">
                <td className="py-2 pr-2">
                  <span className="text-[#94a3b8] mr-2">{player.number}</span>
                  <span className="text-white">{player.name}</span>
                </td>
                <td className="text-right py-2 px-2 text-white">{player.rec}</td>
                <td className="text-right py-2 px-2 text-white">{player.yds}</td>
                <td className="text-right py-2 px-2 text-white">{player.avg.toFixed(1)}</td>
                <td className="text-right py-2 pl-2 text-white">{player.td}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Defense Stats */}
      <div>
        <h4 className="text-[#94a3b8] mb-3">Defense</h4>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[#94a3b8] border-b border-[#2d4a6f]">
              <th className="text-left py-2 pr-2">Player</th>
              <th className="text-right py-2 px-2">Tck/Ast</th>
              <th className="text-right py-2 px-2">Sack</th>
              <th className="text-right py-2 pl-2">Int</th>
            </tr>
          </thead>
          <tbody>
            {team.playerStats.defense.map((player, idx) => (
              <tr key={idx} className="border-b border-[#2d4a6f]/30">
                <td className="py-2 pr-2">
                  <span className="text-[#94a3b8] mr-2">{player.number}</span>
                  <span className="text-white">{player.name}</span>
                </td>
                <td className="text-right py-2 px-2 text-white">{player.tck}/{player.ast}</td>
                <td className="text-right py-2 px-2 text-white">{player.sack.toFixed(1)}</td>
                <td className="text-right py-2 pl-2 text-white">{player.int}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Kick Returns */}
      <div>
        <h4 className="text-[#94a3b8] mb-3">Kick Returns</h4>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[#94a3b8] border-b border-[#2d4a6f]">
              <th className="text-left py-2 pr-2">Player</th>
              <th className="text-right py-2 px-2">Ret</th>
              <th className="text-right py-2 px-2">Yds</th>
              <th className="text-right py-2 px-2">Avg</th>
              <th className="text-right py-2 pl-2">TD</th>
            </tr>
          </thead>
          <tbody>
            {team.playerStats.kickReturns.map((player, idx) => (
              <tr key={idx} className="border-b border-[#2d4a6f]/30">
                <td className="py-2 pr-2">
                  <span className="text-[#94a3b8] mr-2">{player.number}</span>
                  <span className="text-white">{player.name}</span>
                </td>
                <td className="text-right py-2 px-2 text-white">{player.ret}</td>
                <td className="text-right py-2 px-2 text-white">{player.yds}</td>
                <td className="text-right py-2 px-2 text-white">{player.avg.toFixed(1)}</td>
                <td className="text-right py-2 pl-2 text-white">{player.td}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Punt Returns */}
      <div>
        <h4 className="text-[#94a3b8] mb-3">Punt Returns</h4>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[#94a3b8] border-b border-[#2d4a6f]">
              <th className="text-left py-2 pr-2">Player</th>
              <th className="text-right py-2 px-2">Ret</th>
              <th className="text-right py-2 px-2">Yds</th>
              <th className="text-right py-2 px-2">Avg</th>
              <th className="text-right py-2 pl-2">TD</th>
            </tr>
          </thead>
          <tbody>
            {team.playerStats.puntReturns.map((player, idx) => (
              <tr key={idx} className="border-b border-[#2d4a6f]/30">
                <td className="py-2 pr-2">
                  <span className="text-[#94a3b8] mr-2">{player.number}</span>
                  <span className="text-white">{player.name}</span>
                </td>
                <td className="text-right py-2 px-2 text-white">{player.ret}</td>
                <td className="text-right py-2 px-2 text-white">{player.yds}</td>
                <td className="text-right py-2 px-2 text-white">{player.avg.toFixed(1)}</td>
                <td className="text-right py-2 pl-2 text-white">{player.td}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Kicking */}
      <div>
        <h4 className="text-[#94a3b8] mb-3">Kicking</h4>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[#94a3b8] border-b border-[#2d4a6f]">
              <th className="text-left py-2 pr-2">Player</th>
              <th className="text-right py-2 px-2">FG</th>
              <th className="text-right py-2 px-2">Pct</th>
              <th className="text-right py-2 px-2">Lng</th>
              <th className="text-right py-2 pl-2">Pts</th>
            </tr>
          </thead>
          <tbody>
            {team.playerStats.kicking.map((player, idx) => (
              <tr key={idx} className="border-b border-[#2d4a6f]/30">
                <td className="py-2 pr-2">
                  <span className="text-[#94a3b8] mr-2">{player.number}</span>
                  <span className="text-white">{player.name}</span>
                </td>
                <td className="text-right py-2 px-2 text-white">{player.fg_made}/{player.fg_att}</td>
                <td className="text-right py-2 px-2 text-white">{player.pct.toFixed(1)}</td>
                <td className="text-right py-2 px-2 text-white">{player.lng}</td>
                <td className="text-right py-2 pl-2 text-white">{player.pts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Punting */}
      <div>
        <h4 className="text-[#94a3b8] mb-3">Punting</h4>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-[#94a3b8] border-b border-[#2d4a6f]">
              <th className="text-left py-2 pr-2">Player</th>
              <th className="text-right py-2 px-2">No</th>
              <th className="text-right py-2 px-2">Yds</th>
              <th className="text-right py-2 px-2">Avg</th>
              <th className="text-right py-2 pl-2">In20</th>
            </tr>
          </thead>
          <tbody>
            {team.playerStats.punting.map((player, idx) => (
              <tr key={idx} className="border-b border-[#2d4a6f]/30">
                <td className="py-2 pr-2">
                  <span className="text-[#94a3b8] mr-2">{player.number}</span>
                  <span className="text-white">{player.name}</span>
                </td>
                <td className="text-right py-2 px-2 text-white">{player.no}</td>
                <td className="text-right py-2 px-2 text-white">{player.yds}</td>
                <td className="text-right py-2 px-2 text-white">{player.avg.toFixed(1)}</td>
                <td className="text-right py-2 pl-2 text-white">{player.in20}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f] flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-white">Box Score</h3>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handlePrevious}
              disabled={currentGameIndex === 0 || loading}
              className="h-8 w-8 p-0 text-white hover:bg-[#2d4a6f] disabled:opacity-30"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-[#d4af37] text-sm min-w-[60px] text-center">
              {loading ? "..." : `Week ${data?.week}`}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleNext}
              disabled={currentGameIndex === DEMO_GAMES.length - 1 || loading}
              className="h-8 w-8 p-0 text-white hover:bg-[#2d4a6f] disabled:opacity-30"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
        {isDemo && <p className="text-[#94a3b8] text-xs">(demo)</p>}
      </div>

      {error && (
        <div className="p-4">
          <Alert className="bg-[#991b1b]/20 border-[#dc2626] text-white">
            <AlertDescription className="text-sm">
              {error}
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Content - Scrollable */}
      <div className="flex-1 overflow-auto p-4 min-h-0">
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-32 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-24 w-full bg-[#2d4a6f]" />
          </div>
        ) : data ? (
          <div className="space-y-4">
            {/* Score Summary */}
            <div className="bg-[#0a1929] rounded-lg p-4">
              <div className="grid grid-cols-6 gap-2 text-center">
                <div className="text-[#94a3b8] text-xs">Team</div>
                <div className="text-[#94a3b8] text-xs">Q1</div>
                <div className="text-[#94a3b8] text-xs">Q2</div>
                <div className="text-[#94a3b8] text-xs">Q3</div>
                <div className="text-[#94a3b8] text-xs">Q4</div>
                <div className="text-[#94a3b8] text-xs">Final</div>
              </div>
              
              {/* Away Team */}
              <div className="grid grid-cols-6 gap-2 text-center mt-2 py-2 border-b border-[#2d4a6f]">
                <div className="text-white">{data.away.team_id}</div>
                <div className="text-white text-sm">{data.away.q1}</div>
                <div className="text-white text-sm">{data.away.q2}</div>
                <div className="text-white text-sm">{data.away.q3}</div>
                <div className="text-white text-sm">{data.away.q4}</div>
                <div className={`${data.away.score > data.home.score ? 'text-[#4ade80]' : 'text-white'}`}>
                  {data.away.score}
                </div>
              </div>

              {/* Home Team */}
              <div className="grid grid-cols-6 gap-2 text-center mt-2 py-2">
                <div className="text-white">{data.home.team_id}</div>
                <div className="text-white text-sm">{data.home.q1}</div>
                <div className="text-white text-sm">{data.home.q2}</div>
                <div className="text-white text-sm">{data.home.q3}</div>
                <div className="text-white text-sm">{data.home.q4}</div>
                <div className={`${data.home.score > data.away.score ? 'text-[#4ade80]' : 'text-white'}`}>
                  {data.home.score}
                </div>
              </div>
            </div>

            {/* Team Stats Comparison */}
            <div>
              <h4 className="text-white mb-3 text-sm">Team Comparison</h4>
              <div className="space-y-3">
                {/* First Downs */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-white">{data.away.first_downs}</span>
                    <span className="text-[#94a3b8]">First Downs</span>
                    <span className="text-white">{data.home.first_downs}</span>
                  </div>
                  <div className="flex gap-1">
                    <Progress 
                      value={(data.away.first_downs / (data.away.first_downs + data.home.first_downs)) * 100} 
                      className="h-2 flex-1 rotate-180" 
                    />
                    <Progress 
                      value={(data.home.first_downs / (data.away.first_downs + data.home.first_downs)) * 100} 
                      className="h-2 flex-1" 
                    />
                  </div>
                </div>

                {/* Total Yards */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-white">{data.away.total_yards}</span>
                    <span className="text-[#94a3b8]">Total Yards</span>
                    <span className="text-white">{data.home.total_yards}</span>
                  </div>
                  <div className="flex gap-1">
                    <Progress 
                      value={(data.away.total_yards / (data.away.total_yards + data.home.total_yards)) * 100} 
                      className="h-2 flex-1 rotate-180" 
                    />
                    <Progress 
                      value={(data.home.total_yards / (data.away.total_yards + data.home.total_yards)) * 100} 
                      className="h-2 flex-1" 
                    />
                  </div>
                </div>

                {/* Passing Yards */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-white">{data.away.pass_yards}</span>
                    <span className="text-[#94a3b8]">Passing Yards</span>
                    <span className="text-white">{data.home.pass_yards}</span>
                  </div>
                  <div className="flex gap-1">
                    <Progress 
                      value={(data.away.pass_yards / (data.away.pass_yards + data.home.pass_yards)) * 100} 
                      className="h-2 flex-1 rotate-180" 
                    />
                    <Progress 
                      value={(data.home.pass_yards / (data.away.pass_yards + data.home.pass_yards)) * 100} 
                      className="h-2 flex-1" 
                    />
                  </div>
                </div>

                {/* Rushing Yards */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-white">{data.away.rush_yards}</span>
                    <span className="text-[#94a3b8]">Rushing Yards</span>
                    <span className="text-white">{data.home.rush_yards}</span>
                  </div>
                  <div className="flex gap-1">
                    <Progress 
                      value={(data.away.rush_yards / (data.away.rush_yards + data.home.rush_yards)) * 100} 
                      className="h-2 flex-1 rotate-180" 
                    />
                    <Progress 
                      value={(data.home.rush_yards / (data.away.rush_yards + data.home.rush_yards)) * 100} 
                      className="h-2 flex-1" 
                    />
                  </div>
                </div>

                {/* Turnovers */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-white">{data.away.turnovers}</span>
                    <span className="text-[#94a3b8]">Turnovers</span>
                    <span className="text-white">{data.home.turnovers}</span>
                  </div>
                  <div className="flex gap-1">
                    <Progress 
                      value={(data.away.turnovers / Math.max(data.away.turnovers + data.home.turnovers, 1)) * 100} 
                      className="h-2 flex-1 rotate-180" 
                    />
                    <Progress 
                      value={(data.home.turnovers / Math.max(data.away.turnovers + data.home.turnovers, 1)) * 100} 
                      className="h-2 flex-1" 
                    />
                  </div>
                </div>

                {/* Time of Possession */}
                <div>
                  <div className="flex justify-between text-xs">
                    <span className="text-white">{data.away.time_of_possession}</span>
                    <span className="text-[#94a3b8]">Time of Possession</span>
                    <span className="text-white">{data.home.time_of_possession}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Game Leaders */}
            <div>
              <h4 className="text-white mb-3 text-sm">Game Leaders</h4>
              <div className="grid grid-cols-2 gap-4">
                {/* Away Team */}
                <div className="space-y-3">
                  <div className="text-[#d4af37] text-xs mb-2">{data.away.team_id}</div>
                  
                  <div>
                    <div className="text-[#94a3b8] text-xs">Passing</div>
                    <div className="text-white text-sm">{data.away.passing_leader.name}</div>
                    <div className="text-[#94a3b8] text-xs">{data.away.passing_leader.stats}</div>
                  </div>

                  <div>
                    <div className="text-[#94a3b8] text-xs">Rushing</div>
                    <div className="text-white text-sm">{data.away.rushing_leader.name}</div>
                    <div className="text-[#94a3b8] text-xs">{data.away.rushing_leader.stats}</div>
                  </div>

                  <div>
                    <div className="text-[#94a3b8] text-xs">Receiving</div>
                    <div className="text-white text-sm">{data.away.receiving_leader.name}</div>
                    <div className="text-[#94a3b8] text-xs">{data.away.receiving_leader.stats}</div>
                  </div>
                </div>

                {/* Home Team */}
                <div className="space-y-3">
                  <div className="text-[#d4af37] text-xs mb-2">{data.home.team_id}</div>
                  
                  <div>
                    <div className="text-[#94a3b8] text-xs">Passing</div>
                    <div className="text-white text-sm">{data.home.passing_leader.name}</div>
                    <div className="text-[#94a3b8] text-xs">{data.home.passing_leader.stats}</div>
                  </div>

                  <div>
                    <div className="text-[#94a3b8] text-xs">Rushing</div>
                    <div className="text-white text-sm">{data.home.rushing_leader.name}</div>
                    <div className="text-[#94a3b8] text-xs">{data.home.rushing_leader.stats}</div>
                  </div>

                  <div>
                    <div className="text-[#94a3b8] text-xs">Receiving</div>
                    <div className="text-white text-sm">{data.home.receiving_leader.name}</div>
                    <div className="text-[#94a3b8] text-xs">{data.home.receiving_leader.stats}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Team Tabs */}
            <div className="border-t border-[#2d4a6f] pt-4">
              <div className="flex gap-2 mb-4">
                <button
                  onClick={() => setSelectedTeam('away')}
                  className={`px-4 py-2 rounded text-sm transition-colors ${
                    selectedTeam === 'away'
                      ? 'bg-[#d4af37] text-[#0a1929]'
                      : 'bg-[#2d4a6f] text-white hover:bg-[#3d5a7f]'
                  }`}
                >
                  {data.away.team_id}
                </button>
                <button
                  onClick={() => setSelectedTeam('home')}
                  className={`px-4 py-2 rounded text-sm transition-colors ${
                    selectedTeam === 'home'
                      ? 'bg-[#d4af37] text-[#0a1929]'
                      : 'bg-[#2d4a6f] text-white hover:bg-[#3d5a7f]'
                  }`}
                >
                  {data.home.team_id}
                </button>
              </div>

              {/* Scrollable Detailed Player Statistics */}
              <div className="max-h-[400px] overflow-y-auto pr-2">
                {renderPlayerStats(selectedTeam === 'away' ? data.away : data.home)}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-[#94a3b8] text-center py-8">No box score available.</p>
        )}
      </div>
    </div>
  );
}
