import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Sheet, SheetContent } from './ui/sheet';
import { Dialog, DialogContent } from './ui/dialog';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { Filter, Download, LayoutGrid, BarChart3 } from 'lucide-react';
import { RosterTable } from './RosterTable';
import { PlayerDrawer } from './PlayerDrawer';
import { FilterPanel } from './FilterPanel';
import { DepthChartModal } from './DepthChartModal';
import { DepthChartMini } from './DepthChartMini';
import { PlayerCardPanel } from './PlayerCardPanel';
import { ContractSnapshot } from './ContractSnapshot';
import { InjuryReport } from './InjuryReport';
import { PlayerRow, DepthSlot, ContractSummary, InjuryRow } from '../types/roster';

// Convert legacy Player interface to new PlayerRow DTO
interface LegacyPlayer {
  name: string;
  num: number;
  pos: string;
  age: number;
  ovr: number;
  spd: number;
  str: number;
  agi: number;
  tpw: number;
  tac: number;
  cth: number;
  tck: number;
  awr: number;
  pot: number;
  sta: number;
  inj: number;
  mor: number;
  ctr: string;
  yrs: number;
  dep: string;
  hlth: string;
  trd: boolean;
}

interface PlayerStats {
  name: string;
  pos: string;
  G: number;
  GS: number;
  Snaps: number;
  OVR: number;
  DEP: string;
  // QB stats
  Att?: number;
  Cmp?: number;
  CmpPct?: number;
  Yds?: number;
  TD?: number;
  INT?: number;
  YA?: number;
  Sack?: number;
  Rate?: number;
  // RB stats
  Rush?: number;
  Fum?: number;
  Tgt?: number;
  Rec?: number;
  RecYds?: number;
  RecTD?: number;
  // WR/TE stats
  Drop?: number;
  YR?: number;
  YAC?: number;
  // DEF stats
  Tkl?: number;
  TFL?: number;
  Sk?: number;
  QBHits?: number;
  Pressures?: number;
  PD?: number;
  FF?: number;
  FR?: number;
  // ST stats
  FG?: number;
  FGA?: number;
  FGPct?: number;
  XP?: number;
  XPA?: number;
  XPPct?: number;
  Punts?: number;
  Avg?: number;
  Net?: number;
}

// Convert legacy player data to new PlayerRow DTO
function convertToPlayerRow(legacyPlayer: LegacyPlayer): PlayerRow {
  return {
    player_id: `P_${legacyPlayer.pos}_${legacyPlayer.num}`,
    name: legacyPlayer.name,
    pos: legacyPlayer.pos,
    age: legacyPlayer.age,
    ovr: legacyPlayer.ovr,
    pot: legacyPlayer.pot,
    contract: {
      years: legacyPlayer.yrs,
      aav: parseInt(legacyPlayer.ctr.replace(/[$,M]/g, '')) * 1000000, // Convert to actual number
      exp: 2025 + legacyPlayer.yrs
    },
    status: {
      injury: legacyPlayer.hlth === 'Healthy' ? undefined : legacyPlayer.hlth,
      eta: legacyPlayer.hlth === 'D' ? '2-4 weeks' : legacyPlayer.hlth === 'Q' ? 'Game-time decision' : undefined
    }
  };
}

const DEMO_ROSTER: LegacyPlayer[] = [
  { name: "J. Kingsley", num: 12, pos: "QB", age: 28, ovr: 84, spd: 78, str: 62, agi: 82, tpw: 91, tac: 86, cth: 48, tck: 22, awr: 85, pot: 88, sta: 92, inj: 18, mor: 74, ctr: "$8.5M", yrs: 2, dep: "QB1", hlth: "Q", trd: false },
  { name: "T. Morrow", num: 22, pos: "RB", age: 26, ovr: 82, spd: 90, str: 74, agi: 88, tpw: 40, tac: 42, cth: 76, tck: 35, awr: 78, pot: 85, sta: 88, inj: 12, mor: 79, ctr: "$4.2M", yrs: 3, dep: "RB1", hlth: "Healthy", trd: false },
  { name: "K. Benton", num: 11, pos: "WR", age: 27, ovr: 87, spd: 93, str: 68, agi: 91, tpw: 36, tac: 44, cth: 90, tck: 28, awr: 83, pot: 90, sta: 90, inj: 22, mor: 81, ctr: "$12.0M", yrs: 4, dep: "WR1", hlth: "Healthy", trd: true },
  { name: "M. Sanders", num: 7, pos: "QB", age: 24, ovr: 71, spd: 81, str: 58, agi: 79, tpw: 84, tac: 78, cth: 42, tck: 18, awr: 72, pot: 82, sta: 88, inj: 15, mor: 76, ctr: "$1.8M", yrs: 1, dep: "QB2", hlth: "Healthy", trd: false },
  { name: "D. Wright", num: 33, pos: "RB", age: 23, ovr: 76, spd: 88, str: 69, agi: 84, tpw: 38, tac: 40, cth: 72, tck: 32, awr: 74, pot: 83, sta: 85, inj: 20, mor: 82, ctr: "$2.1M", yrs: 2, dep: "RB2", hlth: "Healthy", trd: false },
  { name: "R. Hayes", num: 28, pos: "RB", age: 29, ovr: 79, spd: 86, str: 72, agi: 82, tpw: 35, tac: 38, cth: 74, tck: 30, awr: 80, pot: 79, sta: 82, inj: 25, mor: 68, ctr: "$3.5M", yrs: 1, dep: "RB3", hlth: "D", trd: false },
  { name: "L. Carter", num: 13, pos: "WR", age: 25, ovr: 83, spd: 91, str: 65, agi: 88, tpw: 34, tac: 42, cth: 88, tck: 26, awr: 81, pot: 87, sta: 87, inj: 18, mor: 85, ctr: "$6.8M", yrs: 3, dep: "WR2", hlth: "Healthy", trd: false },
  { name: "J. Thomas", num: 18, pos: "WR", age: 22, ovr: 74, spd: 92, str: 61, agi: 90, tpw: 32, tac: 40, cth: 82, tck: 24, awr: 73, pot: 85, sta: 90, inj: 12, mor: 88, ctr: "$1.2M", yrs: 2, dep: "WR3", hlth: "Healthy", trd: false },
  { name: "A. Rodriguez", num: 84, pos: "WR", age: 30, ovr: 80, spd: 88, str: 67, agi: 85, tpw: 36, tac: 44, cth: 85, tck: 28, awr: 84, pot: 78, sta: 84, inj: 28, mor: 72, ctr: "$5.2M", yrs: 2, dep: "WR4", hlth: "Healthy", trd: false },
  { name: "C. Matthews", num: 87, pos: "TE", age: 27, ovr: 85, spd: 82, str: 78, agi: 80, tpw: 38, tac: 45, cth: 86, tck: 48, awr: 82, pot: 86, sta: 88, inj: 20, mor: 80, ctr: "$7.5M", yrs: 3, dep: "TE1", hlth: "Healthy", trd: false },
  { name: "B. Wilson", num: 88, pos: "TE", age: 24, ovr: 77, spd: 79, str: 75, agi: 77, tpw: 36, tac: 42, cth: 80, tck: 45, awr: 76, pot: 82, sta: 86, inj: 16, mor: 84, ctr: "$2.4M", yrs: 2, dep: "TE2", hlth: "Healthy", trd: false },
  { name: "T. Garcia", num: 65, pos: "C", age: 29, ovr: 81, spd: 68, str: 88, agi: 70, tpw: 30, tac: 35, cth: 55, tck: 62, awr: 84, pot: 80, sta: 90, inj: 22, mor: 78, ctr: "$5.8M", yrs: 2, dep: "C1", hlth: "Healthy", trd: false },
  { name: "M. Johnson", num: 72, pos: "G", age: 26, ovr: 79, spd: 66, str: 86, agi: 68, tpw: 28, tac: 32, cth: 52, tck: 60, awr: 80, pot: 84, sta: 88, inj: 18, mor: 82, ctr: "$4.5M", yrs: 3, dep: "LG1", hlth: "Healthy", trd: false },
  { name: "K. Brown", num: 73, pos: "G", age: 28, ovr: 80, spd: 67, str: 87, agi: 69, tpw: 29, tac: 33, cth: 53, tck: 61, awr: 81, pot: 81, sta: 89, inj: 20, mor: 76, ctr: "$5.1M", yrs: 2, dep: "RG1", hlth: "Q", trd: false },
  { name: "D. Miller", num: 76, pos: "T", age: 25, ovr: 82, spd: 70, str: 90, agi: 72, tpw: 31, tac: 36, cth: 54, tck: 64, awr: 82, pot: 86, sta: 91, inj: 16, mor: 84, ctr: "$6.2M", yrs: 4, dep: "LT1", hlth: "Healthy", trd: false },
  { name: "J. Davis", num: 77, pos: "T", age: 27, ovr: 83, spd: 71, str: 91, agi: 73, tpw: 32, tac: 37, cth: 55, tck: 65, awr: 83, pot: 84, sta: 92, inj: 19, mor: 79, ctr: "$6.8M", yrs: 3, dep: "RT1", hlth: "Healthy", trd: false },
  { name: "R. Anderson", num: 92, pos: "DE", age: 26, ovr: 84, spd: 80, str: 85, agi: 78, tpw: 34, tac: 38, cth: 58, tck: 78, awr: 82, pot: 87, sta: 86, inj: 24, mor: 81, ctr: "$8.2M", yrs: 3, dep: "DE1", hlth: "Healthy", trd: false },
  { name: "S. Taylor", num: 95, pos: "DE", age: 29, ovr: 82, spd: 78, str: 84, agi: 76, tpw: 33, tac: 37, cth: 56, tck: 76, awr: 84, pot: 81, sta: 84, inj: 26, mor: 74, ctr: "$7.1M", yrs: 2, dep: "DE2", hlth: "Healthy", trd: false },
  { name: "P. Williams", num: 98, pos: "DT", age: 27, ovr: 80, spd: 72, str: 92, agi: 70, tpw: 30, tac: 34, cth: 52, tck: 70, awr: 81, pot: 83, sta: 88, inj: 22, mor: 77, ctr: "$5.9M", yrs: 3, dep: "DT1", hlth: "Healthy", trd: false },
  { name: "L. Jackson", num: 54, pos: "LB", age: 25, ovr: 85, spd: 82, str: 80, agi: 84, tpw: 35, tac: 40, cth: 62, tck: 82, awr: 85, pot: 88, sta: 90, inj: 18, mor: 86, ctr: "$9.5M", yrs: 4, dep: "MLB1", hlth: "Healthy", trd: false },
  { name: "E. Harris", num: 52, pos: "LB", age: 28, ovr: 83, spd: 80, str: 79, agi: 82, tpw: 34, tac: 39, cth: 60, tck: 80, awr: 84, pot: 82, sta: 88, inj: 21, mor: 78, ctr: "$7.8M", yrs: 2, dep: "OLB1", hlth: "Healthy", trd: false },
  { name: "M. White", num: 58, pos: "LB", age: 24, ovr: 78, spd: 81, str: 76, agi: 83, tpw: 33, tac: 38, cth: 58, tck: 76, awr: 79, pot: 84, sta: 86, inj: 16, mor: 84, ctr: "$3.2M", yrs: 3, dep: "OLB2", hlth: "Healthy", trd: false },
  { name: "C. Robinson", num: 24, pos: "CB", age: 26, ovr: 86, spd: 94, str: 68, agi: 92, tpw: 32, tac: 38, cth: 78, tck: 65, awr: 84, pot: 88, sta: 89, inj: 17, mor: 83, ctr: "$10.2M", yrs: 4, dep: "CB1", hlth: "Healthy", trd: false },
  { name: "D. Lewis", num: 23, pos: "CB", age: 27, ovr: 84, spd: 93, str: 67, agi: 91, tpw: 31, tac: 37, cth: 76, tck: 64, awr: 83, pot: 85, sta: 87, inj: 19, mor: 80, ctr: "$8.9M", yrs: 3, dep: "CB2", hlth: "Q", trd: false },
  { name: "T. Young", num: 25, pos: "CB", age: 23, ovr: 76, spd: 92, str: 64, agi: 90, tpw: 30, tac: 36, cth: 72, tck: 60, awr: 75, pot: 86, sta: 88, inj: 14, mor: 86, ctr: "$1.8M", yrs: 2, dep: "CB3", hlth: "Healthy", trd: false },
  { name: "A. Green", num: 21, pos: "S", age: 28, ovr: 85, spd: 88, str: 74, agi: 86, tpw: 34, tac: 40, cth: 74, tck: 74, awr: 86, pot: 84, sta: 90, inj: 20, mor: 79, ctr: "$8.8M", yrs: 3, dep: "FS1", hlth: "Healthy", trd: false },
  { name: "J. Adams", num: 26, pos: "S", age: 25, ovr: 82, spd: 86, str: 72, agi: 84, tpw: 33, tac: 39, cth: 72, tck: 72, awr: 83, pot: 86, sta: 88, inj: 18, mor: 82, ctr: "$6.5M", yrs: 3, dep: "SS1", hlth: "Healthy", trd: false },
  { name: "N. Parker", num: 3, pos: "K", age: 26, ovr: 79, spd: 65, str: 60, agi: 68, tpw: 28, tac: 30, cth: 50, tck: 42, awr: 78, pot: 82, sta: 85, inj: 10, mor: 80, ctr: "$2.8M", yrs: 2, dep: "K1", hlth: "Healthy", trd: false },
  { name: "B. Collins", num: 1, pos: "P", age: 29, ovr: 77, spd: 64, str: 58, agi: 66, tpw: 27, tac: 29, cth: 48, tck: 40, awr: 80, pot: 76, sta: 84, inj: 12, mor: 76, ctr: "$2.1M", yrs: 1, dep: "P1", hlth: "Healthy", trd: false },
];

const DEMO_STATS: PlayerStats[] = [
  { name: "J. Kingsley", pos: "QB", G: 5, GS: 5, Snaps: 320, OVR: 84, DEP: "QB1", Att: 172, Cmp: 118, CmpPct: 68.6, Yds: 1420, TD: 10, INT: 4, YA: 8.3, Sack: 9, Rate: 101.4 },
  { name: "T. Morrow", pos: "RB", G: 5, GS: 5, Snaps: 250, OVR: 82, DEP: "RB1", Rush: 92, Yds: 418, YA: 4.5, TD: 4, Fum: 1, Tgt: 18, Rec: 14, RecYds: 102, RecTD: 1 },
  { name: "K. Benton", pos: "WR", G: 5, GS: 5, Snaps: 285, OVR: 87, DEP: "WR1", Tgt: 45, Rec: 29, Yds: 412, YR: 14.2, TD: 3, Drop: 2, YAC: 118 },
  { name: "M. Sanders", pos: "QB", G: 2, GS: 0, Snaps: 45, OVR: 71, DEP: "QB2", Att: 18, Cmp: 11, CmpPct: 61.1, Yds: 124, TD: 1, INT: 1, YA: 6.9, Sack: 2, Rate: 78.5 },
  { name: "D. Wright", pos: "RB", G: 5, GS: 2, Snaps: 180, OVR: 76, DEP: "RB2", Rush: 58, Yds: 248, YA: 4.3, TD: 2, Fum: 0, Tgt: 12, Rec: 9, RecYds: 68, RecTD: 0 },
  { name: "R. Hayes", pos: "RB", G: 3, GS: 0, Snaps: 65, OVR: 79, DEP: "RB3", Rush: 24, Yds: 98, YA: 4.1, TD: 1, Fum: 0, Tgt: 5, Rec: 4, RecYds: 28, RecTD: 0 },
  { name: "L. Carter", pos: "WR", G: 5, GS: 5, Snaps: 270, OVR: 83, DEP: "WR2", Tgt: 38, Rec: 24, Yds: 342, YR: 14.3, TD: 2, Drop: 1, YAC: 98 },
  { name: "J. Thomas", pos: "WR", G: 5, GS: 3, Snaps: 220, OVR: 74, DEP: "WR3", Tgt: 28, Rec: 18, Yds: 224, YR: 12.4, TD: 1, Drop: 2, YAC: 72 },
  { name: "C. Matthews", pos: "TE", G: 5, GS: 5, Snaps: 265, OVR: 85, DEP: "TE1", Tgt: 32, Rec: 22, Yds: 268, YR: 12.2, TD: 3, Drop: 1, YAC: 85 },
];

export function RosterPage() {
  const [viewMode, setViewMode] = useState<'attributes' | 'stats'>('attributes');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPlayer, setSelectedPlayer] = useState<PlayerRow | null>(null);
  const [filterOpen, setFilterOpen] = useState(false);
  const [depthChartOpen, setDepthChartOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [players, setPlayers] = useState<PlayerRow[]>([]);
  const [depthChart, setDepthChart] = useState<DepthSlot[]>([]);
  const [contractSummary, setContractSummary] = useState<ContractSummary>({
    cap_space: 15000000,
    top_contracts: [
      { player_id: 'P_WR_11', name: 'K. Benton', pos: 'WR', aav: 12000000 },
      { player_id: 'P_LB_54', name: 'L. Jackson', pos: 'LB', aav: 9500000 },
      { player_id: 'P_CB_24', name: 'C. Robinson', pos: 'CB', aav: 10200000 },
      { player_id: 'P_TE_87', name: 'C. Matthews', pos: 'TE', aav: 7500000 },
      { player_id: 'P_QB_12', name: 'J. Kingsley', pos: 'QB', aav: 8500000 }
    ],
    expiring: [
      { player_id: 'P_RB_28', name: 'R. Hayes', pos: 'RB', aav: 3500000, exp_year: 2026 },
      { player_id: 'P_CB_23', name: 'D. Lewis', pos: 'CB', aav: 8900000, exp_year: 2026 },
      { player_id: 'P_S_21', name: 'A. Green', pos: 'S', aav: 8800000, exp_year: 2026 }
    ]
  });
  const [injuries, setInjuries] = useState<InjuryRow[]>([
    { player_id: 'P_QB_12', type: 'Shoulder', severity: 'Minor', weeks_remaining: 1, rtp_penalty: 0.05 },
    { player_id: 'P_RB_28', type: 'Hamstring', severity: 'Moderate', weeks_remaining: 3, rtp_penalty: 0.15 },
    { player_id: 'P_CB_23', type: 'Ankle', severity: 'Minor', weeks_remaining: 1, rtp_penalty: 0.05 }
  ]);
  const [stats, setStats] = useState<PlayerStats[]>([]);

  useEffect(() => {
    const timer = setTimeout(() => {
      const convertedPlayers = DEMO_ROSTER.map(convertToPlayerRow);
      setPlayers(convertedPlayers);
      setStats(DEMO_STATS);
      setLoading(false);
    }, 800);

    return () => clearTimeout(timer);
  }, []);

  const positionQuotas = {
    QB: { current: 2, min: 2 },
    RB: { current: 3, min: 3 },
    WR: { current: 4, min: 5 },
    TE: { current: 2, min: 2 },
    C: { current: 1, min: 1 },
    G: { current: 2, min: 2 },
    T: { current: 2, min: 2 },
    DE: { current: 2, min: 2 },
    DT: { current: 1, min: 1 },
    LB: { current: 3, min: 6 },
    CB: { current: 3, min: 4 },
    S: { current: 2, min: 4 },
    K: { current: 1, min: 1 },
    P: { current: 1, min: 1 },
  };

  return (
    <div className="max-w-[1800px] mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <Select defaultValue="NE">
              <SelectTrigger className="w-[200px] bg-[#1a2332] border-[#2d4a6f] text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                <SelectItem value="NE">New England Patriots</SelectItem>
              </SelectContent>
            </Select>
            <h1 className="text-white">Active Roster</h1>
          </div>

          <div className="flex items-center gap-3">
            {/* View Toggle */}
            <div className="flex items-center bg-[#1a2332] rounded-lg border border-[#2d4a6f] p-1">
              <button
                onClick={() => setViewMode('attributes')}
                className={`px-4 py-2 rounded text-sm transition-colors ${
                  viewMode === 'attributes'
                    ? 'bg-[#d4af37] text-[#0a1929]'
                    : 'text-white hover:bg-[#2d4a6f]'
                }`}
              >
                Attributes
              </button>
              <button
                onClick={() => setViewMode('stats')}
                className={`px-4 py-2 rounded text-sm transition-colors ${
                  viewMode === 'stats'
                    ? 'bg-[#d4af37] text-[#0a1929]'
                    : 'text-white hover:bg-[#2d4a6f]'
                }`}
              >
                Stats
              </button>
            </div>

            <Button
              variant="outline"
              className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
            >
              Auto Assign
            </Button>

            <Button
              onClick={() => setFilterOpen(true)}
              variant="outline"
              className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
            >
              <Filter className="h-4 w-4 mr-2" />
              Filter
            </Button>

            <Button
              variant="outline"
              className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
              disabled
            >
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Search and Position Quotas */}
        <div className="space-y-3">
          <Input
            type="text"
            placeholder="Search name, position, or query like OVR >= 75 AND CTH >= 80"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-[#1a2332] border-[#2d4a6f] text-white placeholder:text-[#94a3b8]"
          />

          {/* Position Quota Widget */}
          <div className="flex flex-wrap gap-2">
            <div className="text-[#94a3b8] text-sm mr-2">Position Quotas:</div>
            {Object.entries(positionQuotas).map(([pos, { current, min }]) => {
              const status = current < min ? 'under' : current === min ? 'exact' : 'over';
              const bgColor = status === 'under' ? 'bg-red-500/20 text-red-400' : 
                             status === 'exact' ? 'bg-amber-500/20 text-amber-400' : 
                             'bg-green-500/20 text-green-400';
              
              return (
                <div
                  key={pos}
                  className={`px-2 py-1 rounded text-xs ${bgColor}`}
                >
                  {pos} {current}/{min}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main Layout per GDD v3.2 §9.2.2.1 */}
      <div className="grid grid-cols-12 gap-6">
        {/* C1: Roster Table + Depth Chart Mini */}
        <div className="col-span-5 space-y-6">
          {/* Roster Table */}
          <RosterTable
            players={players}
            stats={stats}
            viewMode={viewMode}
            loading={loading}
            error={error}
            searchQuery={searchQuery}
            onPlayerClick={setSelectedPlayer}
          />

          {/* Depth Chart Mini */}
          <DepthChartMini
            players={players}
            depthChart={depthChart}
            onDepthChartChange={setDepthChart}
            onPlayerClick={setSelectedPlayer}
          />
        </div>

        {/* C2: Player Card Panel + Auto-Depth Assign */}
        <div className="col-span-4 space-y-6">
          {/* Player Card Panel */}
          <PlayerCardPanel
            selectedPlayer={selectedPlayer}
            onClose={() => setSelectedPlayer(null)}
          />

          {/* Auto-Depth Assign Button */}
          <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] p-4">
            <div className="text-center">
              <Button
                onClick={() => {
                  // Auto-fill logic will be handled by DepthChartMini
                }}
                className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929] w-full"
              >
                Auto-Depth Assign
              </Button>
              <p className="text-[#94a3b8] text-xs mt-2">
                Automatically assign best available players to depth chart positions
              </p>
            </div>
          </div>
        </div>

        {/* C3: Contract Snapshot + Injury Report */}
        <div className="col-span-3 space-y-6">
          {/* Contract Snapshot */}
          <ContractSnapshot contractSummary={contractSummary} />

          {/* Injury Report */}
          <InjuryReport injuries={injuries} />
        </div>
      </div>

      {/* Player Drawer */}
      {selectedPlayer && (
        <PlayerDrawer
          player={selectedPlayer}
          open={!!selectedPlayer}
          onClose={() => setSelectedPlayer(null)}
        />
      )}

      {/* Filter Panel */}
      <FilterPanel
        open={filterOpen}
        onClose={() => setFilterOpen(false)}
      />
    </div>
  );
}
