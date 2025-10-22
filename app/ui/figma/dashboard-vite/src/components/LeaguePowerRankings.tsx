import { useState, useEffect } from 'react';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { ScrollArea } from './ui/scroll-area';
import { fetchJson, withDemo } from '../utils/fetch';
import { demoPowerRankings } from '../utils/demoData';

interface PowerRanking {
  rank: number;
  team_id: string;
  power: number;
  delta: string;
}

interface PowerRankingsData {
  as_of: string;
  rows: PowerRanking[];
}

// Convert demo data to match the expected structure
const DEMO_DATA: PowerRanking[] = [
  { rank: 1, team_id: "SF", power: 1692, delta: "+2" },
  { rank: 2, team_id: "KC", power: 1684, delta: "-1" },
  { rank: 3, team_id: "BAL", power: 1661, delta: "+1" },
  { rank: 4, team_id: "PHI", power: 1658, delta: "-1" },
  { rank: 5, team_id: "BUF", power: 1648, delta: "+3" },
  { rank: 6, team_id: "DAL", power: 1642, delta: "-1" },
  { rank: 7, team_id: "MIA", power: 1635, delta: "+2" },
  { rank: 8, team_id: "DET", power: 1628, delta: "-2" },
  { rank: 9, team_id: "CLE", power: 1621, delta: "+1" },
  { rank: 10, team_id: "JAX", power: 1615, delta: "-1" },
  { rank: 11, team_id: "LAC", power: 1608, delta: "+2" },
  { rank: 12, team_id: "CIN", power: 1602, delta: "-1" },
  { rank: 13, team_id: "SEA", power: 1595, delta: "+1" },
  { rank: 14, team_id: "NO", power: 1589, delta: "-2" },
  { rank: 15, team_id: "LAR", power: 1582, delta: "+1" },
  { rank: 16, team_id: "GB", power: 1576, delta: "-1" },
  { rank: 17, team_id: "MIN", power: 1569, delta: "0" },
  { rank: 18, team_id: "TB", power: 1562, delta: "+2" },
  { rank: 19, team_id: "PIT", power: 1556, delta: "-1" },
  { rank: 20, team_id: "ATL", power: 1549, delta: "+1" },
  { rank: 21, team_id: "LV", power: 1542, delta: "-2" },
  { rank: 22, team_id: "IND", power: 1535, delta: "+1" },
  { rank: 23, team_id: "HOU", power: 1528, delta: "-1" },
  { rank: 24, team_id: "TEN", power: 1521, delta: "+2" },
  { rank: 25, team_id: "NYJ", power: 1514, delta: "-1" },
  { rank: 26, team_id: "NE", power: 1507, delta: "+1" },
  { rank: 27, team_id: "DEN", power: 1500, delta: "-2" },
  { rank: 28, team_id: "CHI", power: 1475, delta: "+1" },
  { rank: 29, team_id: "WAS", power: 1458, delta: "-1" },
  { rank: 30, team_id: "NYG", power: 1442, delta: "0" },
  { rank: 31, team_id: "ARI", power: 1426, delta: "+1" },
  { rank: 32, team_id: "CAR", power: 1410, delta: "-1" },
];

export function LeaguePowerRankings() {
  const [data, setData] = useState<PowerRanking[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDemo, setIsDemo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const result = await withDemo(
          fetchJson("/power_rankings"),
          demoPowerRankings
        );
        
        if (result.demo) {
          setIsDemo(true);
          setError("Couldn't load rankings. Showing demo.");
          setData(DEMO_DATA);
        } else {
          setIsDemo(false);
          // Convert API response to our expected structure
          const apiData = result.data as PowerRankingsData;
          setData(apiData.rows);
        }
      } catch (err) {
        setIsDemo(true);
        setError(err instanceof Error ? err.message : "Unknown error");
        setData(DEMO_DATA);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] h-[420px] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f] flex-shrink-0">
        <h3 className="text-white">League Power Rankings</h3>
        {isDemo && <p className="text-[#94a3b8] text-xs mt-0.5">(demo)</p>}
      </div>

      {error && (
        <div className="px-4 pt-3 flex-shrink-0">
          <Alert className="bg-[#991b1b]/20 border-[#dc2626] text-white">
            <AlertDescription className="text-sm">
              {error}
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Subheader */}
      {!loading && data && data.length > 5 && (
        <div className="px-4 py-2 bg-[#0a1929] border-b border-[#2d4a6f] flex-shrink-0">
          <p className="text-[#94a3b8] text-xs">Top 5 (scroll to see all {data.length})</p>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {loading ? (
          <div className="p-4 space-y-2">
            <Skeleton className="h-11 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-11 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-11 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-11 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-11 w-full bg-[#2d4a6f]" />
          </div>
        ) : (
          <ScrollArea className="h-full">
            <div className="p-4">
              {data && data.length > 0 ? (
                <div className="space-y-1">
                  {data.map((team) => (
                    <div
                      key={team.rank}
                      className="flex items-center justify-between py-2.5 px-3 hover:bg-[#2d4a6f]/30 rounded transition-colors min-h-[44px]"
                    >
                      <div className="flex items-center gap-3 flex-1">
                        <span className="text-[#94a3b8] text-sm w-6 text-right">{team.rank}</span>
                        <span className="inline-flex items-center justify-center bg-[#1e3a5f] text-white px-2 py-0.5 rounded min-w-[56px] text-sm text-center">
                          {team.team_id}
                        </span>
                        <span className="text-white text-sm">{team.power}</span>
                      </div>
                      <div className="flex-shrink-0">
                        <span
                          className={`text-xs ${
                            team.delta.startsWith('+')
                              ? 'text-[#22c55e]'
                              : team.delta.startsWith('-')
                              ? 'text-[#ef4444]'
                              : 'text-[#94a3b8]'
                          }`}
                        >
                          {team.delta.startsWith('+') && '▲ '}
                          {team.delta.startsWith('-') && '▼ '}
                          {team.delta === '0' && '— '}
                          {team.delta.replace(/^[+-]/, '')}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[#94a3b8] text-center py-8">No rankings data available.</p>
              )}
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  );
}
