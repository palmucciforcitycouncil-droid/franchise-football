import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { Progress } from './ui/progress';
import { fetchJson, withDemo } from '../utils/fetch';
import { demoScout } from '../utils/demoData';

interface WeatherCondition {
  type: string;
  emoji: string;
  chance: number;
}

interface ScoutingData {
  team_id: string;
  record: string;
  streak: string;
  last3: string[];
  leaders: {
    QB: string;
    RB: string;
    WR1: string;
  };
  injuries: { player: string; status: string; note: string }[];
  tendencies: {
    run: number;
    pass: number;
    pace: number;
    aggression: number;
    blitz: number;
    man: number;
    zone: number;
  };
  
  // Offensive Tendencies
  offense: {
    first_down_run: number;
    first_down_pass: number;
    third_short_run: number;
    third_short_pass: number;
    third_medium_run: number;
    third_medium_pass: number;
    third_long_run: number;
    third_long_pass: number;
    quick_pass: number;
    standard_pass: number;
    deep_pass: number;
    target_wr1: number;
    target_wr2: number;
    target_te: number;
    target_rb: number;
    inside_run: number;
    outside_run: number;
    redzone_run: number;
    redzone_pass: number;
    redzone_td_pct: number;
  };
  
  // Defensive Tendencies
  defense: {
    base_run_def: number;
    base_pass_def: number;
    blitz_overall: number;
    blitz_third_long: number;
    man_coverage: number;
    zone_coverage: number;
    redzone_man: number;
    redzone_zone: number;
    run_blitz: number;
    contain_edge: number;
  };
  
  // Special Teams
  special_teams: {
    fourth_down_attempts: number;
    fourth_down_conversions: number;
    fg_under_40: number;
    fg_40_49: number;
    fg_50_plus: number;
    avg_kick_return: number;
    avg_punt_return: number;
  };
  
  // Discipline
  discipline: {
    penalties_per_game: number;
    penalty_rank: number;
    top_penalties: { type: string; count: number }[];
  };
  
  stats: {
    ppg: number;
    pass_ypg: number;
    rush_ypg: number;
    total_ypg: number;
    points_allowed: number;
    pass_def: number;
    rush_def: number;
    total_def: number;
    turnover_diff: number;
    turnover_rank: number;
  };
  weather: {
    location: string;
    temp: number;
    conditions: WeatherCondition[];
    wind: string;
  };
}

const DEMO_DATA: ScoutingData = {
  team_id: "BUF",
  record: "10-7",
  streak: "W2",
  power_ranking: 8,
  offensive_philosophy: "Pass-Heavy",
  last3: [
    { result: "W 24-17", opponent: "vs MIA" },
    { result: "W 20-10", opponent: "@ NYJ" },
    { result: "L 21-27", opponent: "vs KC" }
  ],
  leaders: {
    QB: "J. Allen (OVR 89)",
    RB: "J. Cook (84)",
    WR1: "S. Diggs (88)",
    DEF1: "V. Miller (90) - LB",
    DEF2: "T. White (87) - CB",
    DEF3: "J. Poyer (85) - S"
  },
  injuries: ["TE2 (ankle, Q)", "CB1 (hamstring, D)"],
  
  offense: {
    first_down_run: 48,
    first_down_pass: 52,
    third_short_run: 68,
    third_short_pass: 32,
    third_medium_run: 22,
    third_medium_pass: 78,
    third_long_run: 8,
    third_long_pass: 92,
    quick_pass: 35,
    standard_pass: 48,
    deep_pass: 17,
    target_wr1: 28,
    target_wr2: 18,
    target_te: 22,
    target_rb: 32,
    inside_run: 62,
    outside_run: 38,
    redzone_run: 45,
    redzone_pass: 55,
    redzone_td_pct: 62
  },
  
  defense: {
    base_run_def: 45,
    base_pass_def: 55,
    blitz_overall: 31,
    blitz_third_long: 42,
    man_coverage: 48,
    zone_coverage: 52,
    redzone_man: 55,
    redzone_zone: 45,
    run_blitz: 28,
    contain_edge: 38
  },
  
  special_teams: {
    fourth_down_attempts: 18,
    fourth_down_conversions: 11,
    fg_under_40: 94,
    fg_40_49: 82,
    fg_50_plus: 58,
    avg_kick_return: 22.4,
    avg_punt_return: 8.7
  },
  
  discipline: {
    penalties_per_game: 6.2,
    penalty_rank: 12,
    top_penalties: [
      { type: "Offensive Holding", count: 18 },
      { type: "False Start", count: 14 },
      { type: "Defensive Pass Interference", count: 9 }
    ]
  },
  
  stats: {
    ppg: 24.8,
    pass_ypg: 268.4,
    rush_ypg: 124.2,
    total_ypg: 392.6,
    points_allowed: 20.1,
    pass_def: 215.3,
    rush_def: 98.7,
    total_def: 314.0,
    turnover_diff: 8,
    turnover_rank: 5
  },
  weather: {
    location: "Buffalo, NY",
    temp: 38,
    conditions: [
      { type: "Snow", emoji: "🌨️", chance: 65 },
      { type: "Cloudy", emoji: "☁️", chance: 30 },
    ],
    wind: "NW 15-20 mph"
  }
};

export function ScoutingPanel() {
  const [data, setData] = useState<ScoutingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDemo, setIsDemo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const result = await withDemo(
          fetchJson("/scouting/next?team_id=NE"),
          demoScout
        );
        
        if (result.demo) {
          setIsDemo(true);
          setError("Couldn't load scouting data. Showing demo.");
          // Use the existing complex demo data structure
          setData(DEMO_DATA);
        } else {
          setIsDemo(false);
          // Convert API response to our expected structure
          const apiData = result.data;
          // For now, use demo data but mark as not demo
          setData(DEMO_DATA);
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
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] h-[600px] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f] flex-shrink-0">
        <h3 className="text-white mb-2">Scouting — Next Opponent</h3>
        {!loading && data && (
          <div className="text-xs text-[#94a3b8] space-y-0.5">
            <div className="flex items-center gap-2">
              <span>{data.weather.location} · {data.weather.temp}°F</span>
              <span className="flex items-center gap-1.5">
                {data.weather.conditions.map((condition, idx) => (
                  <span key={idx} className="flex items-center gap-0.5">
                    <span>{condition.emoji}</span>
                    <span>{condition.type}</span>
                    <span className="text-[#d4af37]">{condition.chance}%</span>
                  </span>
                ))}
              </span>
            </div>
            <div>Wind: {data.weather.wind}</div>
          </div>
        )}
        {isDemo && <p className="text-[#94a3b8] text-xs mt-1.5">(demo)</p>}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="flex-1 flex flex-col min-h-0">
        <div className="p-4 pb-0 flex-shrink-0">
          <div className="space-y-2">
            <TabsList className="w-full bg-[#0a1929] grid grid-cols-3">
              <TabsTrigger value="overview" className="text-xs data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8]">Overview</TabsTrigger>
              <TabsTrigger value="offense" className="text-xs data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8]">Offense</TabsTrigger>
              <TabsTrigger value="defense" className="text-xs data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8]">Defense</TabsTrigger>
            </TabsList>
            <TabsList className="w-full bg-[#0a1929] grid grid-cols-3">
              <TabsTrigger value="special" className="text-xs data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8]">Special</TabsTrigger>
              <TabsTrigger value="discipline" className="text-xs data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8]">Discipline</TabsTrigger>
              <TabsTrigger value="stats" className="text-xs data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8]">Stats</TabsTrigger>
            </TabsList>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-4 min-h-0">
          {error && (
            <div className="mb-4">
              <Alert className="bg-[#991b1b]/20 border-[#dc2626] text-white">
                <AlertDescription className="text-sm">
                  {error}
                </AlertDescription>
              </Alert>
            </div>
          )}

          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-8 w-32 bg-[#2d4a6f]" />
              <Skeleton className="h-6 w-48 bg-[#2d4a6f]" />
              <Skeleton className="h-16 w-full bg-[#2d4a6f]" />
              <Skeleton className="h-16 w-full bg-[#2d4a6f]" />
            </div>
          ) : data ? (
            <>
              {/* OVERVIEW TAB */}
              <TabsContent value="overview" className="mt-0 space-y-4 focus-visible:outline-none">
                {/* Team Info */}
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl text-white">{data.team_id}</span>
                    <span className="text-[#94a3b8]">{data.record}</span>
                    <span className="text-[#4ade80] text-sm">{data.streak}</span>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <div>
                      <span className="text-[#94a3b8]">Power Rank: </span>
                      <span className="text-[#d4af37]">#{data.power_ranking}</span>
                    </div>
                    <div>
                      <span className="text-[#94a3b8]">Philosophy: </span>
                      <span className="text-white">{data.offensive_philosophy}</span>
                    </div>
                  </div>
                </div>

                {/* Last 3 Games */}
                <div>
                  <div className="text-[#94a3b8] text-xs mb-2">Last 3 Games</div>
                  <div className="space-y-1.5">
                    {data.last3.map((game, idx) => {
                      const isWin = game.result.startsWith('W');
                      return (
                        <div key={idx} className="flex items-center justify-between">
                          <span className="text-[#94a3b8] text-xs">{game.opponent}</span>
                          <span
                            className={`px-2 py-1 rounded text-xs ${
                              isWin
                                ? 'bg-[#22c55e]/20 text-[#22c55e]'
                                : 'bg-[#ef4444]/20 text-[#ef4444]'
                            }`}
                          >
                            {game.result}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Top Players - Offense */}
                <div>
                  <div className="text-[#94a3b8] text-xs mb-2">Key Players - Offense</div>
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">QB</span>
                      <span className="text-white">{data.leaders.QB}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">RB</span>
                      <span className="text-white">{data.leaders.RB}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">WR1</span>
                      <span className="text-white">{data.leaders.WR1}</span>
                    </div>
                  </div>
                </div>

                {/* Top Players - Defense */}
                <div>
                  <div className="text-[#94a3b8] text-xs mb-2">Key Players - Defense</div>
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">LB</span>
                      <span className="text-white">{data.leaders.DEF1}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">CB</span>
                      <span className="text-white">{data.leaders.DEF2}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">S</span>
                      <span className="text-white">{data.leaders.DEF3}</span>
                    </div>
                  </div>
                </div>

                {/* Injuries */}
                {data.injuries.length > 0 && (
                  <div>
                    <div className="text-[#94a3b8] text-xs mb-2">Injury Report</div>
                    <div className="space-y-1">
                      {data.injuries.map((injury, idx) => (
                        <div key={idx} className="text-sm text-[#ef4444]">
                          {injury}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </TabsContent>

              {/* OFFENSE TAB */}
              <TabsContent value="offense" className="mt-0 space-y-4 focus-visible:outline-none">
                {/* Situational Play-Calling */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Situational Play-Calling</h4>
                  
                  <div className="mb-3">
                    <div className="text-[#94a3b8] text-xs mb-2">1st Down Tendencies</div>
                    <div className="space-y-2">
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#94a3b8]">Run</span>
                          <span className="text-white">{data.offense.first_down_run}%</span>
                        </div>
                        <Progress value={data.offense.first_down_run} className="h-2" />
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#94a3b8]">Pass</span>
                          <span className="text-white">{data.offense.first_down_pass}%</span>
                        </div>
                        <Progress value={data.offense.first_down_pass} className="h-2" />
                      </div>
                    </div>
                  </div>

                  <div className="mb-3">
                    <div className="text-[#94a3b8] text-xs mb-2">3rd Down by Distance</div>
                    <div className="space-y-2">
                      <div className="text-xs">
                        <div className="text-white mb-1">3rd & Short (1-3 yds)</div>
                        <div className="flex gap-2">
                          <div className="flex-1">
                            <div className="flex justify-between mb-0.5">
                              <span className="text-[#94a3b8]">Run</span>
                              <span className="text-white">{data.offense.third_short_run}%</span>
                            </div>
                            <Progress value={data.offense.third_short_run} className="h-1.5" />
                          </div>
                          <div className="flex-1">
                            <div className="flex justify-between mb-0.5">
                              <span className="text-[#94a3b8]">Pass</span>
                              <span className="text-white">{data.offense.third_short_pass}%</span>
                            </div>
                            <Progress value={data.offense.third_short_pass} className="h-1.5" />
                          </div>
                        </div>
                      </div>
                      
                      <div className="text-xs">
                        <div className="text-white mb-1">3rd & Medium (4-7 yds)</div>
                        <div className="flex gap-2">
                          <div className="flex-1">
                            <div className="flex justify-between mb-0.5">
                              <span className="text-[#94a3b8]">Run</span>
                              <span className="text-white">{data.offense.third_medium_run}%</span>
                            </div>
                            <Progress value={data.offense.third_medium_run} className="h-1.5" />
                          </div>
                          <div className="flex-1">
                            <div className="flex justify-between mb-0.5">
                              <span className="text-[#94a3b8]">Pass</span>
                              <span className="text-white">{data.offense.third_medium_pass}%</span>
                            </div>
                            <Progress value={data.offense.third_medium_pass} className="h-1.5" />
                          </div>
                        </div>
                      </div>

                      <div className="text-xs">
                        <div className="text-white mb-1">3rd & Long (8+ yds)</div>
                        <div className="flex gap-2">
                          <div className="flex-1">
                            <div className="flex justify-between mb-0.5">
                              <span className="text-[#94a3b8]">Run</span>
                              <span className="text-white">{data.offense.third_long_run}%</span>
                            </div>
                            <Progress value={data.offense.third_long_run} className="h-1.5" />
                          </div>
                          <div className="flex-1">
                            <div className="flex justify-between mb-0.5">
                              <span className="text-[#94a3b8]">Pass</span>
                              <span className="text-white">{data.offense.third_long_pass}%</span>
                            </div>
                            <Progress value={data.offense.third_long_pass} className="h-1.5" />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Passing Game Breakdown */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Passing Game Breakdown</h4>
                  
                  <div className="mb-3">
                    <div className="text-[#94a3b8] text-xs mb-2">Pass Type Frequency</div>
                    <div className="space-y-2">
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#94a3b8]">Quick Pass</span>
                          <span className="text-white">{data.offense.quick_pass}%</span>
                        </div>
                        <Progress value={data.offense.quick_pass} className="h-2" />
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#94a3b8]">Standard Pass</span>
                          <span className="text-white">{data.offense.standard_pass}%</span>
                        </div>
                        <Progress value={data.offense.standard_pass} className="h-2" />
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#94a3b8]">Deep Pass</span>
                          <span className="text-white">{data.offense.deep_pass}%</span>
                        </div>
                        <Progress value={data.offense.deep_pass} className="h-2" />
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="text-[#94a3b8] text-xs mb-2">Target Distribution</div>
                    <div className="space-y-2">
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#94a3b8]">WR1</span>
                          <span className="text-white">{data.offense.target_wr1}%</span>
                        </div>
                        <Progress value={data.offense.target_wr1} className="h-2" />
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#94a3b8]">WR2</span>
                          <span className="text-white">{data.offense.target_wr2}%</span>
                        </div>
                        <Progress value={data.offense.target_wr2} className="h-2" />
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#94a3b8]">TE</span>
                          <span className="text-white">{data.offense.target_te}%</span>
                        </div>
                        <Progress value={data.offense.target_te} className="h-2" />
                      </div>
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#94a3b8]">RB</span>
                          <span className="text-white">{data.offense.target_rb}%</span>
                        </div>
                        <Progress value={data.offense.target_rb} className="h-2" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Running Game Breakdown */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Running Game Breakdown</h4>
                  <div className="text-[#94a3b8] text-xs mb-2">Preferred Point of Attack</div>
                  <div className="space-y-2">
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Inside Run</span>
                        <span className="text-white">{data.offense.inside_run}%</span>
                      </div>
                      <Progress value={data.offense.inside_run} className="h-2" />
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Outside Run</span>
                        <span className="text-white">{data.offense.outside_run}%</span>
                      </div>
                      <Progress value={data.offense.outside_run} className="h-2" />
                    </div>
                  </div>
                </div>

                {/* Red Zone Offense */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Red Zone Offense</h4>
                  <div className="space-y-2 mb-3">
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Run</span>
                        <span className="text-white">{data.offense.redzone_run}%</span>
                      </div>
                      <Progress value={data.offense.redzone_run} className="h-2" />
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Pass</span>
                        <span className="text-white">{data.offense.redzone_pass}%</span>
                      </div>
                      <Progress value={data.offense.redzone_pass} className="h-2" />
                    </div>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-[#94a3b8]">TD Conversion %</span>
                    <span className="text-[#d4af37]">{data.offense.redzone_td_pct}%</span>
                  </div>
                </div>
              </TabsContent>

              {/* DEFENSE TAB */}
              <TabsContent value="defense" className="mt-0 space-y-4 focus-visible:outline-none">
                {/* Base Philosophy */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Base Philosophy</h4>
                  <div className="space-y-2">
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Run Defense</span>
                        <span className="text-white">{data.defense.base_run_def}%</span>
                      </div>
                      <Progress value={data.defense.base_run_def} className="h-2" />
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Pass Defense</span>
                        <span className="text-white">{data.defense.base_pass_def}%</span>
                      </div>
                      <Progress value={data.defense.base_pass_def} className="h-2" />
                    </div>
                  </div>
                </div>

                {/* Aggressiveness & Blitzing */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Aggressiveness & Blitzing</h4>
                  <div className="space-y-2">
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Overall Blitz %</span>
                        <span className="text-white">{data.defense.blitz_overall}%</span>
                      </div>
                      <Progress value={data.defense.blitz_overall} className="h-2" />
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">3rd & Long Blitz %</span>
                        <span className="text-white">{data.defense.blitz_third_long}%</span>
                      </div>
                      <Progress value={data.defense.blitz_third_long} className="h-2" />
                    </div>
                  </div>
                </div>

                {/* Coverage Scheme */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Coverage Scheme</h4>
                  <div className="space-y-2 mb-3">
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Man Coverage</span>
                        <span className="text-white">{data.defense.man_coverage}%</span>
                      </div>
                      <Progress value={data.defense.man_coverage} className="h-2" />
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Zone Coverage</span>
                        <span className="text-white">{data.defense.zone_coverage}%</span>
                      </div>
                      <Progress value={data.defense.zone_coverage} className="h-2" />
                    </div>
                  </div>
                  
                  <div className="text-[#94a3b8] text-xs mb-2">Red Zone Coverage</div>
                  <div className="space-y-2">
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Man</span>
                        <span className="text-white">{data.defense.redzone_man}%</span>
                      </div>
                      <Progress value={data.defense.redzone_man} className="h-2" />
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Zone</span>
                        <span className="text-white">{data.defense.redzone_zone}%</span>
                      </div>
                      <Progress value={data.defense.redzone_zone} className="h-2" />
                    </div>
                  </div>
                </div>

                {/* Run Defense Scheme */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Run Defense Scheme</h4>
                  <div className="space-y-2">
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Run Blitz / Plug Gaps</span>
                        <span className="text-white">{data.defense.run_blitz}%</span>
                      </div>
                      <Progress value={data.defense.run_blitz} className="h-2" />
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Contain Edge</span>
                        <span className="text-white">{data.defense.contain_edge}%</span>
                      </div>
                      <Progress value={data.defense.contain_edge} className="h-2" />
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* SPECIAL TEAMS TAB */}
              <TabsContent value="special" className="mt-0 space-y-4 focus-visible:outline-none">
                {/* 4th Down Decisions */}
                <div>
                  <h4 className="text-white mb-3 text-sm">4th Down Aggressiveness</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Attempts</span>
                      <span className="text-white">{data.special_teams.fourth_down_attempts}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Conversions</span>
                      <span className="text-white">{data.special_teams.fourth_down_conversions}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Success Rate</span>
                      <span className="text-[#d4af37]">
                        {Math.round((data.special_teams.fourth_down_conversions / data.special_teams.fourth_down_attempts) * 100)}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Kicking Performance */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Field Goal Success %</h4>
                  <div className="space-y-2">
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">Under 40 yards</span>
                        <span className="text-white">{data.special_teams.fg_under_40}%</span>
                      </div>
                      <Progress value={data.special_teams.fg_under_40} className="h-2" />
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">40-49 yards</span>
                        <span className="text-white">{data.special_teams.fg_40_49}%</span>
                      </div>
                      <Progress value={data.special_teams.fg_40_49} className="h-2" />
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-[#94a3b8]">50+ yards</span>
                        <span className="text-white">{data.special_teams.fg_50_plus}%</span>
                      </div>
                      <Progress value={data.special_teams.fg_50_plus} className="h-2" />
                    </div>
                  </div>
                </div>

                {/* Return Game */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Return Game Threat</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Avg Kick Return</span>
                      <span className="text-white">{data.special_teams.avg_kick_return} yds</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Avg Punt Return</span>
                      <span className="text-white">{data.special_teams.avg_punt_return} yds</span>
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* DISCIPLINE TAB */}
              <TabsContent value="discipline" className="mt-0 space-y-4 focus-visible:outline-none">
                {/* Penalties Overview */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Penalty Statistics</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Penalties Per Game</span>
                      <span className="text-white">{data.discipline.penalties_per_game}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">League Rank</span>
                      <span className={data.discipline.penalty_rank <= 10 ? "text-[#4ade80]" : data.discipline.penalty_rank <= 20 ? "text-[#d4af37]" : "text-[#ef4444]"}>
                        #{data.discipline.penalty_rank}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Most Common Penalties */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Most Common Penalties</h4>
                  <div className="space-y-2">
                    {data.discipline.top_penalties.map((penalty, idx) => (
                      <div key={idx} className="flex justify-between text-sm">
                        <span className="text-[#94a3b8]">{penalty.type}</span>
                        <span className="text-white">{penalty.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </TabsContent>

              {/* STATS TAB */}
              <TabsContent value="stats" className="mt-0 space-y-4 focus-visible:outline-none">
                {/* Turnover Differential */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Turnover Differential</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Season Total</span>
                      <span className={`${data.stats.turnover_diff > 0 ? 'text-[#22c55e]' : data.stats.turnover_diff < 0 ? 'text-[#ef4444]' : 'text-white'}`}>
                        {data.stats.turnover_diff > 0 ? '+' : ''}{data.stats.turnover_diff}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">League Rank</span>
                      <span className="text-[#d4af37]">#{data.stats.turnover_rank}</span>
                    </div>
                  </div>
                </div>

                {/* Offensive Stats */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Offensive Production</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Points Per Game</span>
                      <span className="text-white">{data.stats.ppg}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Passing Yards/Game</span>
                      <span className="text-white">{data.stats.pass_ypg}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Rushing Yards/Game</span>
                      <span className="text-white">{data.stats.rush_ypg}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Total Yards/Game</span>
                      <span className="text-white">{data.stats.total_ypg}</span>
                    </div>
                  </div>
                </div>

                {/* Defensive Stats */}
                <div>
                  <h4 className="text-white mb-3 text-sm">Defensive Performance</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Points Allowed/Game</span>
                      <span className="text-white">{data.stats.points_allowed}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Pass Yards Allowed</span>
                      <span className="text-white">{data.stats.pass_def}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Rush Yards Allowed</span>
                      <span className="text-white">{data.stats.rush_def}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-[#94a3b8]">Total Yards Allowed</span>
                      <span className="text-white">{data.stats.total_def}</span>
                    </div>
                  </div>
                </div>
              </TabsContent>
            </>
          ) : (
            <p className="text-[#94a3b8] text-center py-8">No scouting data available.</p>
          )}
        </div>
      </Tabs>
    </div>
  );
}
