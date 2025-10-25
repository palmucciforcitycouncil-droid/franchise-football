import { useState, useEffect } from 'react';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { ScrollArea } from './ui/scroll-area';

interface ScheduleGame {
  week: number;
  home: boolean;
  opp: string;
  opp_record: string;
  team_id: string;
  score_team?: number;
  score_opp?: number;
  result?: 'W' | 'L' | 'T';
  record: string;
}

const DEMO_DATA: ScheduleGame[] = [
  { week: 1, home: true, opp: "BUF", opp_record: "10-7", team_id: "NE", score_team: 24, score_opp: 21, result: "W", record: "8-9" },
  { week: 2, home: false, opp: "MIA", opp_record: "9-8", team_id: "NE", score_team: 17, score_opp: 28, result: "L", record: "8-9" },
  { week: 3, home: true, opp: "NYJ", opp_record: "4-13", team_id: "NE", score_team: 31, score_opp: 14, result: "W", record: "8-9" },
  { week: 4, home: false, opp: "BAL", opp_record: "11-6", team_id: "NE", score_team: 20, score_opp: 27, result: "L", record: "8-9" },
  { week: 5, home: true, opp: "CIN", opp_record: "9-8", team_id: "NE", score_team: 35, score_opp: 21, result: "W", record: "8-9" },
  { week: 6, home: false, opp: "PIT", opp_record: "8-9", team_id: "NE", score_team: 14, score_opp: 17, result: "L", record: "8-9" },
  { week: 7, home: true, opp: "CLE", opp_record: "7-10", team_id: "NE", score_team: 28, score_opp: 24, result: "W", record: "8-9" },
  { week: 8, home: false, opp: "LAC", opp_record: "10-7", team_id: "NE", score_team: 21, score_opp: 24, result: "L", record: "8-9" },
  { week: 9, home: true, opp: "KC", opp_record: "12-5", team_id: "NE", score_team: 17, score_opp: 31, result: "L", record: "8-9" },
  { week: 10, home: false, opp: "DEN", opp_record: "6-11", team_id: "NE", score_team: 27, score_opp: 20, result: "W", record: "8-9" },
  { week: 11, home: true, opp: "LV", opp_record: "5-12", team_id: "NE", score_team: 24, score_opp: 21, result: "W", record: "8-9" },
  { week: 12, home: false, opp: "SEA", opp_record: "9-8", team_id: "NE", score_team: 20, score_opp: 23, result: "L", record: "8-9" },
  { week: 13, home: true, opp: "SF", opp_record: "13-4", team_id: "NE", score_team: 14, score_opp: 28, result: "L", record: "8-9" },
  { week: 14, home: false, opp: "ARI", opp_record: "3-14", team_id: "NE", score_team: 31, score_opp: 17, result: "W", record: "8-9" },
  { week: 15, home: true, opp: "LAR", opp_record: "10-7", team_id: "NE", score_team: 21, score_opp: 24, result: "L", record: "8-9" },
  { week: 16, home: false, opp: "MIA", opp_record: "9-8", team_id: "NE", score_team: 28, score_opp: 14, result: "W", record: "8-9" },
  { week: 17, home: true, opp: "BUF", opp_record: "10-7", team_id: "NE", score_team: 24, score_opp: 27, result: "L", record: "8-9" },
  { week: 18, home: false, opp: "NYJ", opp_record: "4-13", team_id: "NE", result: undefined, record: "8-9" },
];

export function TeamSchedule() {
  const [data, setData] = useState<ScheduleGame[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    // Simulate API call
    const timer = setTimeout(() => {
      setData(DEMO_DATA);
      setLoading(false);
    }, 600);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] h-[520px] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f] flex-shrink-0">
        <h3 className="text-white">Schedule</h3>
        <p className="text-[#94a3b8] text-xs mt-0.5">(demo)</p>
      </div>

      {error && (
        <div className="px-4 pt-3 flex-shrink-0">
          <Alert className="bg-[#991b1b]/20 border-[#dc2626] text-white">
            <AlertDescription className="text-sm">
              Couldn't load schedule. Showing demo.
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
                          <span className="text-sm">{game.opp}</span>
                          <span className="text-[#94a3b8] text-xs">({game.opp_record})</span>
                        </div>
                        {game.score_team !== undefined && (
                          <div className="text-white">
                            <span className={game.result === 'W' ? 'font-bold' : ''}>
                              {game.team_id} {game.score_team}
                            </span>
                            <span className="text-[#94a3b8] mx-1">-</span>
                            <span className={game.result === 'L' ? 'font-bold' : ''}>
                              {game.opp} {game.score_opp}
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
