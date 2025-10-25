import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Progress } from './ui/progress';
import { ScrollArea } from './ui/scroll-area';

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

interface PlayerDrawerProps {
  player: Player;
  open: boolean;
  onClose: () => void;
}

export function PlayerDrawer({ player, open, onClose }: PlayerDrawerProps) {
  const getHealthColor = (status: string) => {
    switch (status) {
      case 'Healthy': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'Q': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'D': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'O': return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const attributes = [
    { label: 'Speed', value: player.spd, key: 'spd' },
    { label: 'Strength', value: player.str, key: 'str' },
    { label: 'Agility', value: player.agi, key: 'agi' },
    { label: 'Throw Power', value: player.tpw, key: 'tpw' },
    { label: 'Throw Accuracy', value: player.tac, key: 'tac' },
    { label: 'Catching', value: player.cth, key: 'cth' },
    { label: 'Tackling', value: player.tck, key: 'tck' },
    { label: 'Awareness', value: player.awr, key: 'awr' },
    { label: 'Potential', value: player.pot, key: 'pot' },
    { label: 'Stamina', value: player.sta, key: 'sta' },
    { label: 'Injury Proneness', value: player.inj, key: 'inj' },
    { label: 'Morale', value: player.mor, key: 'mor' },
  ];

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#1a2332] border border-[#2d4a6f] max-w-[580px] max-h-[85vh] p-0">
        <DialogHeader className="border-b border-[#2d4a6f] pb-4 mb-0 px-6 pt-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-[#2d4a6f] flex items-center justify-center text-white text-xl">
                {player.num}
              </div>
              <div>
                <DialogTitle className="text-white text-xl mb-1">{player.name}</DialogTitle>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-[#2d4a6f] text-white text-sm">{player.pos}</span>
                  <span className="px-3 py-0.5 rounded bg-[#d4af37]/20 text-[#d4af37] border border-[#d4af37]/30 text-sm">
                    {player.ovr} OVR
                  </span>
                  <span className="px-2 py-0.5 rounded bg-[#2d4a6f] text-[#94a3b8] text-sm">NE</span>
                </div>
              </div>
            </div>
          </div>
          <DialogDescription className="sr-only">
            Player details and statistics for {player.name}
          </DialogDescription>
        </DialogHeader>
        
        <ScrollArea className="h-full px-6 pb-6">`

          {/* Tabs */}
          <Tabs defaultValue="overview" className="w-full mt-4">
          <TabsList className="w-full bg-[#0a1929] mb-4">
            <TabsTrigger value="overview" className="flex-1 data-[state=active]:bg-[#2d4a6f] data-[state=active]:text-white text-[#94a3b8]">
              Overview
            </TabsTrigger>
            <TabsTrigger value="ratings" className="flex-1 data-[state=active]:bg-[#2d4a6f] data-[state=active]:text-white text-[#94a3b8]">
              Ratings
            </TabsTrigger>
            <TabsTrigger value="stats" className="flex-1 data-[state=active]:bg-[#2d4a6f] data-[state=active]:text-white text-[#94a3b8]">
              Stats
            </TabsTrigger>
            <TabsTrigger value="contract" className="flex-1 data-[state=active]:bg-[#2d4a6f] data-[state=active]:text-white text-[#94a3b8]">
              Contract
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-4">
            <div className="bg-[#0a1929] rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[#94a3b8]">Depth Chart</span>
                <span className="text-white">{player.dep}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94a3b8]">Age</span>
                <span className="text-white">{player.age} years old</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94a3b8]">Health Status</span>
                <span className={`px-2 py-0.5 rounded text-xs border ${getHealthColor(player.hlth)}`}>
                  {player.hlth}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94a3b8]">Trade Block</span>
                <span className="text-white">{player.trd ? 'Yes' : 'No'}</span>
              </div>
            </div>

            <div className="bg-[#0a1929] rounded-lg p-4 space-y-3">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[#94a3b8]">Morale</span>
                  <span className="text-white">{player.mor}/100</span>
                </div>
                <Progress value={player.mor} className="h-2" />
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[#94a3b8]">Stamina</span>
                  <span className="text-white">{player.sta}/100</span>
                </div>
                <Progress value={player.sta} className="h-2" />
              </div>
            </div>

            <div className="bg-[#0a1929] rounded-lg p-4">
              <p className="text-[#94a3b8] text-sm leading-relaxed">
                {player.pos === 'QB' && 'Experienced quarterback with strong arm and field awareness.'}
                {player.pos === 'RB' && 'Dynamic running back with excellent speed and agility.'}
                {player.pos === 'WR' && 'Reliable wide receiver with great hands and route running.'}
                {player.pos === 'TE' && 'Versatile tight end who excels in both blocking and receiving.'}
                {['C', 'G', 'T'].includes(player.pos) && 'Solid offensive lineman with good technique and strength.'}
                {['DE', 'DT'].includes(player.pos) && 'Disruptive defensive lineman with pass rush ability.'}
                {player.pos === 'LB' && 'Athletic linebacker with sideline-to-sideline speed.'}
                {player.pos === 'CB' && 'Lockdown cornerback with excellent coverage skills.'}
                {player.pos === 'S' && 'Hard-hitting safety with good ball skills and range.'}
                {player.pos === 'K' && 'Reliable kicker with strong leg and accuracy.'}
                {player.pos === 'P' && 'Consistent punter with good directional control.'}
              </p>
            </div>
          </TabsContent>

          {/* Ratings Tab */}
          <TabsContent value="ratings" className="space-y-3">
            {attributes.map(attr => (
              <div key={attr.key} className="bg-[#0a1929] rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[#94a3b8] text-sm">{attr.label}</span>
                  <span className="text-white tabular-nums">{attr.value}</span>
                </div>
                <Progress value={attr.value} className="h-1.5" />
              </div>
            ))}
          </TabsContent>

          {/* Stats Tab */}
          <TabsContent value="stats" className="space-y-4">
            <div className="bg-[#0a1929] rounded-lg p-4">
              <div className="text-center text-[#94a3b8] py-8">
                <p>Season 2025 Stats</p>
                <p className="text-sm mt-2">Coming soon</p>
              </div>
            </div>
          </TabsContent>

          {/* Contract Tab */}
          <TabsContent value="contract" className="space-y-4">
            <div className="bg-[#0a1929] rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[#94a3b8]">Annual Value</span>
                <span className="text-white text-lg">{player.ctr}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94a3b8]">Years Remaining</span>
                <span className="text-white">{player.yrs} {player.yrs === 1 ? 'year' : 'years'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#94a3b8]">Cap Hit</span>
                <span className="text-white">{player.ctr}</span>
              </div>
            </div>
          </TabsContent>
          </Tabs>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
