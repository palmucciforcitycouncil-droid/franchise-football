import { useState, useEffect } from 'react';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';

interface TeamStanding {
  abbr: string;
  wins: number;
  losses: number;
  ties: number;
  pf: number;
  pa: number;
  power: number;
}

interface DivisionData {
  [key: string]: TeamStanding[];
}

const DEMO_DATA: { AFC: DivisionData; NFC: DivisionData } = {
  AFC: {
    East: [
      { abbr: "BUF", wins: 10, losses: 7, ties: 0, pf: 421, pa: 342, power: 8 },
      { abbr: "MIA", wins: 9, losses: 8, ties: 0, pf: 398, pa: 359, power: 12 },
      { abbr: "NE", wins: 8, losses: 9, ties: 0, pf: 364, pa: 371, power: 18 },
      { abbr: "NYJ", wins: 4, losses: 13, ties: 0, pf: 287, pa: 426, power: 29 }
    ],
    North: [
      { abbr: "BAL", wins: 11, losses: 6, ties: 0, pf: 456, pa: 318, power: 3 },
      { abbr: "CIN", wins: 9, losses: 8, ties: 0, pf: 412, pa: 387, power: 11 },
      { abbr: "PIT", wins: 8, losses: 9, ties: 0, pf: 341, pa: 356, power: 17 },
      { abbr: "CLE", wins: 7, losses: 10, ties: 0, pf: 318, pa: 398, power: 22 }
    ],
    South: [
      { abbr: "JAX", wins: 9, losses: 8, ties: 0, pf: 387, pa: 364, power: 13 },
      { abbr: "TEN", wins: 6, losses: 11, ties: 0, pf: 298, pa: 401, power: 26 },
      { abbr: "IND", wins: 6, losses: 11, ties: 0, pf: 312, pa: 389, power: 25 },
      { abbr: "HOU", wins: 5, losses: 12, ties: 0, pf: 276, pa: 421, power: 28 }
    ],
    West: [
      { abbr: "KC", wins: 12, losses: 5, ties: 0, pf: 478, pa: 312, power: 2 },
      { abbr: "LAC", wins: 10, losses: 7, ties: 0, pf: 423, pa: 356, power: 9 },
      { abbr: "LV", wins: 5, losses: 12, ties: 0, pf: 289, pa: 434, power: 30 },
      { abbr: "DEN", wins: 6, losses: 11, ties: 0, pf: 301, pa: 412, power: 27 }
    ]
  },
  NFC: {
    East: [
      { abbr: "DAL", wins: 11, losses: 6, ties: 0, pf: 445, pa: 334, power: 5 },
      { abbr: "PHI", wins: 10, losses: 7, ties: 0, pf: 421, pa: 348, power: 7 },
      { abbr: "NYG", wins: 5, losses: 12, ties: 0, pf: 298, pa: 423, power: 24 },
      { abbr: "WAS", wins: 4, losses: 13, ties: 0, pf: 267, pa: 445, power: 31 }
    ],
    North: [
      { abbr: "DET", wins: 12, losses: 5, ties: 0, pf: 467, pa: 323, power: 4 },
      { abbr: "GB", wins: 9, losses: 8, ties: 0, pf: 398, pa: 367, power: 14 },
      { abbr: "MIN", wins: 7, losses: 10, ties: 0, pf: 334, pa: 389, power: 20 },
      { abbr: "CHI", wins: 5, losses: 12, ties: 0, pf: 287, pa: 421, power: 28 }
    ],
    South: [
      { abbr: "TB", wins: 8, losses: 9, ties: 0, pf: 356, pa: 378, power: 16 },
      { abbr: "NO", wins: 7, losses: 10, ties: 0, pf: 323, pa: 387, power: 19 },
      { abbr: "ATL", wins: 7, losses: 10, ties: 0, pf: 312, pa: 391, power: 21 },
      { abbr: "CAR", wins: 3, losses: 14, ties: 0, pf: 234, pa: 456, power: 32 }
    ],
    West: [
      { abbr: "SF", wins: 11, losses: 6, ties: 0, pf: 456, pa: 334, power: 1 },
      { abbr: "SEA", wins: 9, losses: 8, ties: 0, pf: 401, pa: 367, power: 10 },
      { abbr: "LAR", wins: 8, losses: 9, ties: 0, pf: 378, pa: 389, power: 15 },
      { abbr: "ARI", wins: 4, losses: 13, ties: 0, pf: 276, pa: 434, power: 23 }
    ]
  }
};

export function DivisionStandings() {
  const [data, setData] = useState<typeof DEMO_DATA | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setData(DEMO_DATA);
      setLoading(false);
    }, 600);

    return () => clearTimeout(timer);
  }, []);

  const renderStandingsTable = (teams: TeamStanding[]) => (
    <table className="w-full">
      <thead>
        <tr className="text-[#94a3b8] text-xs border-b border-[#2d4a6f]">
          <th className="text-left py-2 pr-2">Team</th>
          <th className="text-center py-2 px-2 min-w-[60px]">W-L-T</th>
          <th className="text-right py-2 px-2 min-w-[44px]">PF</th>
          <th className="text-right py-2 px-2 min-w-[44px]">PA</th>
          <th className="text-right py-2 pl-2 min-w-[44px]">Power</th>
        </tr>
      </thead>
      <tbody>
        {teams.map((team) => (
          <tr
            key={team.abbr}
            className="border-b border-[#2d4a6f]/50 hover:bg-[#2d4a6f]/30 transition-colors"
          >
            <td className="py-2.5 pr-2">
              <span className="text-white">{team.abbr}</span>
            </td>
            <td className="py-2.5 px-2 text-center">
              <span className="text-white text-sm">
                {team.wins}-{team.losses}-{team.ties}
              </span>
            </td>
            <td className="py-2.5 px-2 text-right">
              <span className="text-white text-sm">{team.pf}</span>
            </td>
            <td className="py-2.5 px-2 text-right">
              <span className="text-white text-sm">{team.pa}</span>
            </td>
            <td className="py-2.5 pl-2 text-right">
              <span className="text-[#d4af37] text-sm">{team.power}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] h-[520px] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f] flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-white">Standings</h3>
        </div>
        <p className="text-[#94a3b8] text-xs">(demo)</p>
      </div>

      {error && (
        <div className="p-4">
          <Alert className="bg-[#991b1b]/20 border-[#dc2626] text-white">
            <AlertDescription className="text-sm">
              Couldn't load standings. Showing demo.
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Content */}
      <div className="p-4 flex-1 overflow-hidden">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-10 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-10 w-full bg-[#2d4a6f]" />
            <Skeleton className="h-10 w-full bg-[#2d4a6f]" />
          </div>
        ) : data ? (
          <Tabs defaultValue="AFC" className="w-full">
            <TabsList className="w-full bg-[#0a1929] mb-4">
              <TabsTrigger value="AFC" className="flex-1 data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8]">
                AFC
              </TabsTrigger>
              <TabsTrigger value="NFC" className="flex-1 data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8]">
                NFC
              </TabsTrigger>
            </TabsList>

            <TabsContent value="AFC" className="mt-0">
              <Tabs defaultValue="East" className="w-full">
                <TabsList className="w-full bg-[#0a1929] mb-4 grid grid-cols-4">
                  <TabsTrigger value="East" className="data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8] text-xs">
                    East
                  </TabsTrigger>
                  <TabsTrigger value="North" className="data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8] text-xs">
                    North
                  </TabsTrigger>
                  <TabsTrigger value="South" className="data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8] text-xs">
                    South
                  </TabsTrigger>
                  <TabsTrigger value="West" className="data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8] text-xs">
                    West
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="East" className="mt-0 focus-visible:outline-none">
                  {renderStandingsTable(data.AFC.East)}
                </TabsContent>
                <TabsContent value="North" className="mt-0 focus-visible:outline-none">
                  {renderStandingsTable(data.AFC.North)}
                </TabsContent>
                <TabsContent value="South" className="mt-0 focus-visible:outline-none">
                  {renderStandingsTable(data.AFC.South)}
                </TabsContent>
                <TabsContent value="West" className="mt-0 focus-visible:outline-none">
                  {renderStandingsTable(data.AFC.West)}
                </TabsContent>
              </Tabs>
            </TabsContent>

            <TabsContent value="NFC" className="mt-0">
              <Tabs defaultValue="East" className="w-full">
                <TabsList className="w-full bg-[#0a1929] mb-4 grid grid-cols-4">
                  <TabsTrigger value="East" className="data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8] text-xs">
                    East
                  </TabsTrigger>
                  <TabsTrigger value="North" className="data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8] text-xs">
                    North
                  </TabsTrigger>
                  <TabsTrigger value="South" className="data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8] text-xs">
                    South
                  </TabsTrigger>
                  <TabsTrigger value="West" className="data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8] text-xs">
                    West
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="East" className="mt-0 focus-visible:outline-none">
                  {renderStandingsTable(data.NFC.East)}
                </TabsContent>
                <TabsContent value="North" className="mt-0 focus-visible:outline-none">
                  {renderStandingsTable(data.NFC.North)}
                </TabsContent>
                <TabsContent value="South" className="mt-0 focus-visible:outline-none">
                  {renderStandingsTable(data.NFC.South)}
                </TabsContent>
                <TabsContent value="West" className="mt-0 focus-visible:outline-none">
                  {renderStandingsTable(data.NFC.West)}
                </TabsContent>
              </Tabs>
            </TabsContent>
          </Tabs>
        ) : (
          <p className="text-[#94a3b8] text-center py-8">No standings data available.</p>
        )}
      </div>
    </div>
  );
}
