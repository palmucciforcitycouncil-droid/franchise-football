import { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Sheet, SheetContent } from './ui/sheet';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { Filter, Download, LayoutGrid, BarChart3, Users, TrendingUp, Search, X } from 'lucide-react';
import { RosterTable } from './RosterTable';
import { PlayerDrawer } from './PlayerDrawer';
import { FilterPanel } from './FilterPanel';
import { DepthChartCards } from './DepthChartCards';
import { DepthChartPanel } from './DepthChartPanel';
import { AutoFillModal } from './AutoFillModal';
import { TopFreeAgentsBox } from './roster/TopFreeAgentsBox';
import { TradeBlockBox } from './roster/TradeBlockBox';
import { FindPlayerBox } from './gm/FindPlayerBox';
import { getRoster, getDepthChart, autoFillDepthChart, updateDepthChart, AutoFillOptions, DepthChartPayload, PlayerData as DepthChartPlayerData } from '../lib/mockDepthChartApi';
import { toast } from 'sonner@2.0.3';

interface Player {
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
  // Core stats
  G: number;
  GS: number;
  Snaps: number;
  OVR: number;
  DEP: string;
  // Passing (QB)
  Att?: number;
  Cmp?: number;
  CmpPct?: number;
  Yds?: number;
  TD?: number;
  INT?: number;
  YA?: number;
  Sack?: number;
  Rate?: number;
  // Rushing (RB/QB/WR/TE)
  Rush?: number;
  RushYds?: number;
  RushYA?: number;
  RushTD?: number;
  Fum?: number;
  // Receiving (WR/TE/RB)
  Tgt?: number;
  Rec?: number;
  RecYds?: number;
  YR?: number;
  RecTD?: number;
  Drop?: number;
  YAC?: number;
  // Defense (LB/DL/DB)
  Tkl?: number;
  TFL?: number;
  Sk?: number;
  QBHits?: number;
  Pressures?: number;
  DefINT?: number;
  PD?: number;
  FF?: number;
  FR?: number;
  DefTD?: number;
  // Kicking (K)
  FG?: number;
  FGA?: number;
  FGPct?: number;
  XP?: number;
  XPA?: number;
  XPPct?: number;
  Lng?: number;
  // Punting & Returns (P/KR/PR)
  Punts?: number;
  PuntAvg?: number;
  Net?: number;
  In20?: number;
  TB?: number;
  KR?: number;
  KRY?: number;
  KRAvg?: number;
  KRTD?: number;
  PR?: number;
  PRY?: number;
  PRAvg?: number;
  PRTD?: number;
}

const DEMO_ROSTER: Player[] = [
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
  { name: "J. Kingsley", pos: "QB", G: 5, GS: 5, Snaps: 320, OVR: 84, DEP: "QB1", Att: 172, Cmp: 118, CmpPct: 68.6, Yds: 1420, TD: 10, INT: 4, YA: 8.3, Sack: 9, Rate: 101.4, Rush: 12, RushYds: 48, RushYA: 4.0, RushTD: 1, Fum: 0 },
  { name: "T. Morrow", pos: "RB", G: 5, GS: 5, Snaps: 250, OVR: 82, DEP: "RB1", Rush: 92, RushYds: 418, RushYA: 4.5, RushTD: 4, Fum: 1, Tgt: 18, Rec: 14, RecYds: 102, YR: 7.3, RecTD: 1, Drop: 0, YAC: 45 },
  { name: "K. Benton", pos: "WR", G: 5, GS: 5, Snaps: 285, OVR: 87, DEP: "WR1", Tgt: 45, Rec: 29, RecYds: 412, YR: 14.2, RecTD: 3, Drop: 2, YAC: 118, Rush: 2, RushYds: 18, RushYA: 9.0, RushTD: 0 },
  { name: "M. Sanders", pos: "QB", G: 2, GS: 0, Snaps: 45, OVR: 71, DEP: "QB2", Att: 18, Cmp: 11, CmpPct: 61.1, Yds: 124, TD: 1, INT: 1, YA: 6.9, Sack: 2, Rate: 78.5, Rush: 3, RushYds: 14, RushYA: 4.7, RushTD: 0, Fum: 0 },
  { name: "D. Wright", pos: "RB", G: 5, GS: 2, Snaps: 180, OVR: 76, DEP: "RB2", Rush: 58, RushYds: 248, RushYA: 4.3, RushTD: 2, Fum: 0, Tgt: 12, Rec: 9, RecYds: 68, YR: 7.6, RecTD: 0, Drop: 1, YAC: 28 },
  { name: "R. Hayes", pos: "RB", G: 3, GS: 0, Snaps: 65, OVR: 79, DEP: "RB3", Rush: 24, RushYds: 98, RushYA: 4.1, RushTD: 1, Fum: 0, Tgt: 5, Rec: 4, RecYds: 28, YR: 7.0, RecTD: 0, Drop: 0, YAC: 12 },
  { name: "L. Carter", pos: "WR", G: 5, GS: 5, Snaps: 270, OVR: 83, DEP: "WR2", Tgt: 38, Rec: 24, RecYds: 342, YR: 14.3, RecTD: 2, Drop: 1, YAC: 98 },
  { name: "J. Thomas", pos: "WR", G: 5, GS: 3, Snaps: 220, OVR: 74, DEP: "WR3", Tgt: 28, Rec: 18, RecYds: 224, YR: 12.4, RecTD: 1, Drop: 2, YAC: 72 },
  { name: "C. Matthews", pos: "TE", G: 5, GS: 5, Snaps: 265, OVR: 85, DEP: "TE1", Tgt: 32, Rec: 22, RecYds: 268, YR: 12.2, RecTD: 3, Drop: 1, YAC: 85 },
  { name: "R. Anderson", pos: "DE", G: 5, GS: 5, Snaps: 290, OVR: 84, DEP: "DE1", Tkl: 28, TFL: 6, Sk: 4.5, QBHits: 8, Pressures: 18, DefINT: 0, PD: 2, FF: 1, FR: 1, DefTD: 0 },
  { name: "L. Jackson", pos: "LB", G: 5, GS: 5, Snaps: 310, OVR: 85, DEP: "MLB1", Tkl: 42, TFL: 4, Sk: 2.0, QBHits: 3, Pressures: 8, DefINT: 1, PD: 3, FF: 0, FR: 0, DefTD: 0 },
  { name: "C. Robinson", pos: "CB", G: 5, GS: 5, Snaps: 295, OVR: 86, DEP: "CB1", Tkl: 22, TFL: 1, Sk: 0, QBHits: 0, Pressures: 0, DefINT: 2, PD: 8, FF: 1, FR: 0, DefTD: 1 },
  { name: "N. Parker", pos: "K", G: 5, GS: 5, Snaps: 48, OVR: 79, DEP: "K1", FG: 8, FGA: 10, FGPct: 80.0, XP: 18, XPA: 19, XPPct: 94.7, Lng: 52 },
  { name: "B. Collins", pos: "P", G: 5, GS: 5, Snaps: 42, OVR: 77, DEP: "P1", Punts: 28, PuntAvg: 44.2, Net: 40.8, In20: 10, TB: 4 },
];

export function RosterPage() {
  const [viewMode, setViewMode] = useState<'attributes' | 'stats'>('attributes');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [filterOpen, setFilterOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [players, setPlayers] = useState<Player[]>([]);
  const [stats, setStats] = useState<PlayerStats[]>([]);
  const [positionFilter, setPositionFilter] = useState<string | null>(null);
  
  // Depth chart state
  const [autoFillModalOpen, setAutoFillModalOpen] = useState(false);
  const [depthChart, setDepthChart] = useState<DepthChartPayload | null>(null);
  const [depthChartLoading, setDepthChartLoading] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [depthChartWarnings, setDepthChartWarnings] = useState<string[]>([]);
  const [isAutoFilled, setIsAutoFilled] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setPlayers(DEMO_ROSTER);
      setStats(DEMO_STATS);
      setLoading(false);
    }, 800);

    return () => clearTimeout(timer);
  }, []);

  // Calculate position quotas from actual roster
  const positionQuotas = {
    QB: { current: players.filter(p => p.pos === 'QB').length, min: 2 },
    RB: { current: players.filter(p => p.pos === 'RB').length, min: 3 },
    WR: { current: players.filter(p => p.pos === 'WR').length, min: 5 },
    TE: { current: players.filter(p => p.pos === 'TE').length, min: 2 },
    C: { current: players.filter(p => p.pos === 'C').length, min: 1 },
    G: { current: players.filter(p => p.pos === 'G').length, min: 2 },
    T: { current: players.filter(p => p.pos === 'T').length, min: 2 },
    DE: { current: players.filter(p => p.pos === 'DE').length, min: 2 },
    DT: { current: players.filter(p => p.pos === 'DT').length, min: 1 },
    LB: { current: players.filter(p => p.pos === 'LB').length, min: 6 },
    CB: { current: players.filter(p => p.pos === 'CB').length, min: 4 },
    S: { current: players.filter(p => p.pos === 'S').length, min: 4 },
    K: { current: players.filter(p => p.pos === 'K').length, min: 1 },
    P: { current: players.filter(p => p.pos === 'P').length, min: 1 },
    KR: { current: players.filter(p => p.pos === 'KR').length, min: 1 },
    PR: { current: players.filter(p => p.pos === 'PR').length, min: 1 },
  };

  // Depth chart slots (exact counts per spec)
  const depthChartSlots = {
    // Offense
    QB: 2,      // QB1, QB2
    RB: 2,      // RB1, RB2
    WR: 3,      // WR1, WR2, WR3
    TE: 2,      // TE1, TE2
    LT: 1,      // LT
    LG: 1,      // LG
    C: 1,       // C
    RG: 1,      // RG
    RT: 1,      // RT
    // Defense - DL/EDGE
    LDE: 1,     // LDE
    DT: 1,      // DT
    RDE: 1,     // RDE
    // Defense - LB
    MLB: 2,     // MLB1, MLB2
    OLB: 2,     // OLB1, OLB2
    // Defense - DB
    CB: 3,      // CB1, CB2, CB3 (Nickel)
    FS: 1,      // FS
    SS: 1,      // SS
    // Special Teams
    K: 1,       // K
    P: 1,       // P
    KR: 2,      // KR1, KR2
    PR: 2,      // PR1, PR2
  };

  const handlePositionFilterClick = (pos: string) => {
    if (positionFilter === pos) {
      setPositionFilter(null);
    } else {
      setPositionFilter(pos);
    }
  };



  const loadDepthChart = async () => {
    setDepthChartLoading(true);
    try {
      const data = await getDepthChart(1);
      setDepthChart(data);
    } catch (err) {
      console.error('Failed to load depth chart:', err);
      toast.error('Failed to load depth chart');
    } finally {
      setDepthChartLoading(false);
    }
  };

  const handleAutoFillApply = async (options: AutoFillOptions) => {
    setDepthChartLoading(true);
    setAutoFillModalOpen(false); // Close modal immediately
    try {
      const result = await autoFillDepthChart(1, options);
      setDepthChart(result);
      setHasUnsavedChanges(false);
      setIsAutoFilled(true);
      setDepthChartWarnings(result.warnings);
      
      if (result.warnings.length > 0) {
        toast.warning(`Depth chart updated with ${result.warnings.length} warning${result.warnings.length !== 1 ? 's' : ''}`);
      } else {
        toast.success('Depth chart updated successfully');
      }
    } catch (err) {
      console.error('Failed to auto-fill depth chart:', err);
      toast.error('Failed to auto-fill depth chart');
    } finally {
      setDepthChartLoading(false);
    }
  };

  const handleSaveDepthChart = async () => {
    if (!depthChart) return;
    
    try {
      await updateDepthChart(1, depthChart);
      setHasUnsavedChanges(false);
      toast.success('Depth chart saved');
    } catch (err) {
      console.error('Failed to save depth chart:', err);
      toast.error('Failed to save depth chart');
    }
  };

  const handleRevertDepthChart = () => {
    loadDepthChart();
    setHasUnsavedChanges(false);
    toast.info('Changes reverted');
  };

  const handleDepthChartPlayerClick = (player: DepthChartPlayerData) => {
    // Convert DepthChartPlayerData to Player format for the drawer
    const convertedPlayer: Player = {
      name: `${player.first_name} ${player.last_name}`,
      num: player.jersey_number,
      pos: player.position,
      age: player.age,
      ovr: player.ratings.ovr,
      spd: player.ratings.spd,
      str: player.ratings.str,
      agi: player.ratings.agi,
      tpw: player.ratings.thp,
      tac: player.ratings.tha,
      cth: player.ratings.cth,
      tck: player.ratings.tkl,
      awr: player.ratings.awr,
      pot: 75, // Mock value
      sta: player.ratings.sta,
      inj: player.injury_proneness || 50,
      mor: 80, // Mock value
      ctr: '$2.5M',
      yrs: 3,
      dep: 'Starter',
      hlth: player.status === 'Active' ? 'Healthy' : player.status,
      trd: false,
    };
    setSelectedPlayer(convertedPlayer);
  };

  return (
    <div className="max-w-[1920px] mx-auto">

      {/* Controls Row - Team Selection and Actions */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Select defaultValue="NE">
            <SelectTrigger className="w-[200px] bg-[#1a2332] border-[#2d4a6f] text-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
              <SelectItem value="NE">New England Patriots</SelectItem>
            </SelectContent>
          </Select>
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

      {/* Main Roster Table - Full Width */}
      <div className="mb-6">
        <RosterTable
          players={players}
          stats={stats}
          viewMode={viewMode}
          loading={loading}
          error={error}
          searchQuery={searchQuery}
          positionFilter={positionFilter}
          onPlayerClick={setSelectedPlayer}
          positionQuotas={positionQuotas}
          onPositionFilterChange={setPositionFilter}
        />
      </div>

      {/* Top Row - 3 Quick Access Boxes */}
      <div className="grid grid-cols-3 gap-6 mb-6">
        <TopFreeAgentsBox />
        <TradeBlockBox />
        <FindPlayerBox />
      </div>

      {/* Depth Chart Cards - Full Width Below Table */}
      <DepthChartCards 
        players={players} 
        positionQuotas={positionQuotas} 
        depthChartSlots={depthChartSlots}
        onOpenAutoFill={() => setAutoFillModalOpen(true)}
        warnings={depthChartWarnings}
        isAutoFilled={isAutoFilled}
      />

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

      {/* Auto-Fill Modal */}
      <AutoFillModal
        open={autoFillModalOpen}
        onClose={() => setAutoFillModalOpen(false)}
        onApply={handleAutoFillApply}
      />
    </div>
  );
}
