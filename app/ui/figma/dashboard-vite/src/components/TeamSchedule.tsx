import { useState, useEffect } from 'react';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { ScrollArea } from './ui/scroll-area';
import { fetchJson, withDemo } from '../utils/fetch';
import { demoSchedule } from '../utils/demoData';

interface ScheduleGame {
  week: number;
  home: boolean;
  opp_id: string;
  team_pts?: number;
  opp_pts?: number;
  result?: 'W' | 'L' | 'T';
  record_after: string;
}

interface ScheduleData {
  team_id: string;
  season: number;
  games: ScheduleGame[];
}

// Convert demo data to match the expected structure
const DEMO_DATA: ScheduleGame[] = [
  { week: 1, home: true, opp_id: "BUF", team_pts: 24, opp_pts: 21, result: "W", record_after: "1-0" },
  { week: 2, home: false, opp_id: "MIA", team_pts: 17, opp_pts: 28, result: "L", record_after: "1-1" },
  { week: 3, home: true, opp_id: "NYJ", team_pts: 31, opp_pts: 14, result: "W", record_after: "2-1" },
  { week: 4, home: false, opp_id: "BAL", team_pts: 20, opp_pts: 27, result: "L", record_after: "2-2" },
  { week: 5, home: true, opp_id: "CIN", team_pts: 35, opp_pts: 21, result: "W", record_after: "3-2" },
  { week: 6, home: false, opp_id: "PIT", team_pts: 14, opp_pts: 17, result: "L", record_after: "3-3" },
  { week: 7, home: true, opp_id: "CLE", team_pts: 28, opp_pts: 24, result: "W", record_after: "4-3" },
  { week: 8, home: false, opp_id: "LAC", team_pts: 21, opp_pts: 24, result: "L", record_after: "4-4" },
  { week: 9, home: true, opp_id: "KC", team_pts: 17, opp_pts: 31, result: "L", record_after: "4-5" },
  { week: 10, home: false, opp_id: "DEN", team_pts: 27, opp_pts: 20, result: "W", record_after: "5-5" },
  { week: 11, home: true, opp_id: "LV", team_pts: 24, opp_pts: 21, result: "W", record_after: "6-5" },
  { week: 12, home: false, opp_id: "SEA", team_pts: 20, opp_pts: 23, result: "L", record_after: "6-6" },
  { week: 13, home: true, opp_id: "SF", team_pts: 14, opp_pts: 28, result: "L", record_after: "6-7" },
  { week: 14, home: false, opp_id: "ARI", team_pts: 31, opp_pts: 17, result: "W", record_after: "7-7" },
  { week: 15, home: true, opp_id: "LAR", team_pts: 21, opp_pts: 24, result: "L", record_after: "7-8" },
  { week: 16, home: false, opp_id: "MIA", team_pts: 28, opp_pts: 14, result: "W", record_after: "8-8" },
  { week: 17, home: true, opp_id: "BUF", team_pts: 24, opp_pts: 27, result: "L", record_after: "8-9" },
  { week: 18, home: false, opp_id: "NYJ", result: undefined, record_after: "8-9" },
];

export function TeamSchedule() {
  const [data, setData] = useState<ScheduleGame[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDemo, setIsDemo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const result = await withDemo(
          fetchJson("/teams/NE/schedule?season=2025"),
          demoSchedule
        );
        
        if (result.demo) {
          setIsDemo(true);
          setError("Couldn't load schedule. Showing demo.");
          setData(DEMO_DATA);
        } else {
          setIsDemo(false);
          // Convert API response to our expected structure
          const apiData = result.data as ScheduleData;
          setData(apiData.games);
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
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] h-[520px] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f] flex-shrink-0">
        <h3 className="text-white">Schedule</h3>
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
                  {data.map((game) => (
                    <div
                      key={game.week}
                      className="flex items-center justify-between py-2.5 px-3 hover:bg-[#2d4a6f]/30 rounded transition-colors min-h-[44px]"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 text-white mb-1">
                          <span className="text-sm">Week {game.week}</span>
                          <span className="text-[#94a3b8]">{game.home ? 'vs' : '@'}</span>
                          <span className="text-sm">{game.opp_id}</span>
                        </div>
                        {game.team_pts !== undefined && (
                          <div className="text-white">
                            <span className={game.result === 'W' ? 'font-bold' : ''}>
                              NE {game.team_pts}
                            </span>
                            <span className="text-[#94a3b8] mx-1">-</span>
                            <span className={game.result === 'L' ? 'font-bold' : ''}>
                              {game.opp_id} {game.opp_pts}
                            </span>
                          </div>
                        )}
                      </div>
                      <div className="flex-shrink-0 ml-3 w-[56px] text-right">
                        {game.result && (
                          <span
                            className={`inline-flex items-center justify-center px-2.5 py-1 rounded text-xs ${
                              game.result === 'W'
                                ? 'bg-[#22c55e]/20 text-[#22c55e]'
                                : game.result === 'L'
                                ? 'bg-[#ef4444]/20 text-[#ef4444]'
                                : 'bg-[#94a3b8]/20 text-[#94a3b8]'
                            }`}
                          >
                            {game.result}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[#94a3b8] text-center py-8">No games scheduled.</p>
              )}
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  );
}
