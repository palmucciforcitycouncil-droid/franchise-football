import { useState, useEffect } from 'react';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { ScrollArea } from './ui/scroll-area';

interface PowerRanking {
  rank: number;
  team_id: string;
  power: number;
  pf: number;
  pa: number;
  delta: string;
}

const DEMO_DATA: PowerRanking[] = [
  { rank: 1, team_id: "SF", power: 1692, pf: 456, pa: 334, delta: "+2" },
  { rank: 2, team_id: "KC", power: 1684, pf: 478, pa: 312, delta: "-1" },
  { rank: 3, team_id: "BAL", power: 1661, pf: 456, pa: 318, delta: "+1" },
  { rank: 4, team_id: "PHI", power: 1658, pf: 421, pa: 348, delta: "-1" },
  { rank: 5, team_id: "BUF", power: 1648, pf: 421, pa: 342, delta: "+3" },
  { rank: 6, team_id: "DAL", power: 1642, pf: 445, pa: 334, delta: "-1" },
  { rank: 7, team_id: "MIA", power: 1635, pf: 398, pa: 359, delta: "+2" },
  { rank: 8, team_id: "DET", power: 1628, pf: 467, pa: 323, delta: "-2" },
  { rank: 9, team_id: "CLE", power: 1621, pf: 318, pa: 398, delta: "+1" },
  { rank: 10, team_id: "JAX", power: 1615, pf: 387, pa: 364, delta: "-1" },
  { rank: 11, team_id: "LAC", power: 1608, pf: 423, pa: 356, delta: "+2" },
  { rank: 12, team_id: "CIN", power: 1602, pf: 412, pa: 387, delta: "-1" },
  { rank: 13, team_id: "SEA", power: 1595, pf: 401, pa: 367, delta: "+1" },
  { rank: 14, team_id: "NO", power: 1589, pf: 323, pa: 387, delta: "-2" },
  { rank: 15, team_id: "LAR", power: 1582, pf: 378, pa: 389, delta: "+1" },
  { rank: 16, team_id: "GB", power: 1576, pf: 398, pa: 367, delta: "-1" },
  { rank: 17, team_id: "MIN", power: 1569, pf: 334, pa: 389, delta: "0" },
  { rank: 18, team_id: "TB", power: 1562, pf: 356, pa: 378, delta: "+2" },
  { rank: 19, team_id: "PIT", power: 1556, pf: 341, pa: 356, delta: "-1" },
  { rank: 20, team_id: "ATL", power: 1549, pf: 312, pa: 391, delta: "+1" },
  { rank: 21, team_id: "LV", power: 1542, pf: 289, pa: 434, delta: "-2" },
  { rank: 22, team_id: "IND", power: 1535, pf: 312, pa: 389, delta: "+1" },
  { rank: 23, team_id: "HOU", power: 1528, pf: 276, pa: 421, delta: "-1" },
  { rank: 24, team_id: "TEN", power: 1521, pf: 298, pa: 401, delta: "+2" },
  { rank: 25, team_id: "NYJ", power: 1514, pf: 287, pa: 426, delta: "-1" },
  { rank: 26, team_id: "NE", power: 1507, pf: 364, pa: 371, delta: "+1" },
  { rank: 27, team_id: "DEN", power: 1500, pf: 301, pa: 412, delta: "-2" },
  { rank: 28, team_id: "CHI", power: 1475, pf: 287, pa: 421, delta: "+1" },
  { rank: 29, team_id: "WAS", power: 1458, pf: 267, pa: 445, delta: "-1" },
  { rank: 30, team_id: "NYG", power: 1442, pf: 298, pa: 423, delta: "0" },
  { rank: 31, team_id: "ARI", power: 1426, pf: 276, pa: 434, delta: "+1" },
  { rank: 32, team_id: "CAR", power: 1410, pf: 234, pa: 456, delta: "-1" },
];

export function LeaguePowerRankings() {
  const [data, setData] = useState<PowerRanking[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    // Simulate API call
    const timer = setTimeout(() => {
      setData(DEMO_DATA);
      setLoading(false);
    }, 700);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] h-[420px] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f] flex-shrink-0">
        <h3 className="text-white">Power Rankings</h3>
        <p className="text-[#94a3b8] text-xs mt-0.5">(demo)</p>
      </div>

      {error && (
        <div className="px-4 pt-3 flex-shrink-0">
          <Alert className="bg-[#991b1b]/20 border-[#dc2626] text-white">
            <AlertDescription className="text-sm">
              Couldn't load rankings. Showing demo.
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Column Headers */}
      {!loading && data && (
        <div className="px-4 py-3 bg-[#0a1929] border-b border-[#2d4a6f] flex-shrink-0">
          <div className="flex items-center justify-between px-3">
            <div className="flex items-center gap-3 flex-1">
              <span className="text-[#64748b] text-xs w-6 text-right">RK</span>
              <span className="text-[#64748b] text-xs min-w-[56px] text-center">TEAM</span>
              <span className="text-[#64748b] text-xs">PWR</span>
              <span className="text-[#64748b] text-xs">PF-PA</span>
            </div>
            <div className="flex-shrink-0">
              <span className="text-[#64748b] text-xs">CHG</span>
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {loading ? (
          <div className="p-4 space-y-2.5">
            <Skeleton className="h-12 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-12 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-12 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-12 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-12 w-full bg-[#2d4a6f]" />
          </div>
        ) : (
          <ScrollArea className="h-full">
            <div className="p-4 pt-2">
              {data && data.length > 0 ? (
                <div className="space-y-1.5">
                  {data.map((team) => (
                    <div
                      key={team.rank}
                      className="flex items-center justify-between py-3 px-3 hover:bg-[#2d4a6f]/30 rounded transition-colors min-h-[48px]"
                    >
                      <div className="flex items-center gap-3 flex-1">
                        <span className="text-[#94a3b8] w-6 text-right">{team.rank}</span>
                        <span className="inline-flex items-center justify-center bg-[#1e3a5f] text-white px-2 py-1 rounded min-w-[56px] text-center">
                          {team.team_id}
                        </span>
                        <span className="text-white">{team.power}</span>
                        <span className="text-[#64748b] text-sm">{team.pf}-{team.pa}</span>
                      </div>
                      <div className="flex-shrink-0">
                        <span
                          className={`text-sm ${
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
