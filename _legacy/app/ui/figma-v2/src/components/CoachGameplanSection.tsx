import { useState } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { HelpCircle } from 'lucide-react';
import { Label } from './ui/label';

type GameplanType = 'HC';

type GameplanSettings = {
  offensiveAgg: string;
  defensiveAgg: string;
  coverage: string;
  blitz: string;
  rzOffense: string;
  rzDefense: string;
};

const AGGRESSIVENESS_OPTIONS = [
  'Very Conservative',
  'Conservative',
  'Balanced',
  'Aggressive',
  'Very Aggressive'
];

const COVERAGE_OPTIONS = ['Man-Heavy', 'Hybrid', 'Zone-Heavy'];
const BLITZ_OPTIONS = ['Selective', 'Standard', 'Blitz Heavy'];
const RZ_OFFENSE_OPTIONS = ['Power Run', 'Balanced', 'Play-Action Heavy', 'Spread/Shot'];
const RZ_DEFENSE_OPTIONS = ['Bend-Don\'t-Break', 'Balanced', 'Run-Sellout', 'Pressure QB'];

export function CoachGameplanSection({ 
  type,
  coachId 
}: { 
  type: GameplanType;
  coachId: string;
}) {
  const [gameplan, setGameplan] = useState<GameplanSettings>({
    offensiveAgg: 'Balanced',
    defensiveAgg: 'Balanced',
    coverage: 'Hybrid',
    blitz: 'Standard',
    rzOffense: 'Balanced',
    rzDefense: 'Balanced'
  });

  const handleChange = (field: keyof GameplanSettings, value: string) => {
    const updated = { ...gameplan, [field]: value };
    setGameplan(updated);
    handleSave(updated);
  };

  const handleSave = async (settings: GameplanSettings) => {
    // Simulate API call - would be POST /api/v1/gameplan/save
    console.log(`Saving HC gameplan for coach ${coachId}:`, settings);
  };

  return (
    <div className="space-y-3">
      <div className="text-xs text-[#94a3b8] mb-2">Gameplan Settings</div>
      <TooltipProvider>
        <div className="space-y-3">
          {/* Offensive Settings */}
          {/* Offensive Aggressiveness */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Label className="text-xs text-white">Off. Aggressiveness</Label>
              <Tooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-3 w-3 text-[#94a3b8] cursor-help" />
                </TooltipTrigger>
                <TooltipContent 
                  className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-xs"
                  id={`ddl-off-agg-tt-${coachId}`}
                >
                  <p className="text-xs">
                    Controls how bold your offense is. Higher = more early-down passes, 
                    deeper routes, trick plays, and more 4th-down/2-pt attempts.
                  </p>
                </TooltipContent>
              </Tooltip>
            </div>
            <Select 
              value={gameplan.offensiveAgg} 
              onValueChange={(val) => handleChange('offensiveAgg', val)}
            >
              <SelectTrigger 
                id={`ddl-off-agg-${coachId}`}
                className="bg-[#0a1929] border-[#2d4a6f] text-white text-xs h-8"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                {AGGRESSIVENESS_OPTIONS.map(opt => (
                  <SelectItem key={opt} value={opt} className="text-xs">{opt}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Red Zone Offense */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Label className="text-xs text-white">Red Zone Offense</Label>
              <Tooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-3 w-3 text-[#94a3b8] cursor-help" />
                </TooltipTrigger>
                <TooltipContent 
                  className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-xs"
                  id={`ddl-rz-off-tt-${coachId}`}
                >
                  <p className="text-xs">
                    Your personality inside the 20: Power on the ground, Balanced, 
                    Play-Action deception, or Spread to attack space.
                  </p>
                </TooltipContent>
              </Tooltip>
            </div>
            <Select 
              value={gameplan.rzOffense} 
              onValueChange={(val) => handleChange('rzOffense', val)}
            >
              <SelectTrigger 
                id={`ddl-rz-off-${coachId}`}
                className="bg-[#0a1929] border-[#2d4a6f] text-white text-xs h-8"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                {RZ_OFFENSE_OPTIONS.map(opt => (
                  <SelectItem key={opt} value={opt} className="text-xs">{opt}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Defensive Settings */}
          {/* Defensive Aggressiveness */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Label className="text-xs text-white">Def. Aggressiveness</Label>
              <Tooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-3 w-3 text-[#94a3b8] cursor-help" />
                </TooltipTrigger>
                <TooltipContent 
                  className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-xs"
                  id={`ddl-def-agg-tt-${coachId}`}
                >
                  <p className="text-xs">
                    Higher = tighter coverage and more pressure. Increases sacks/negative 
                    plays but risks big explosives.
                  </p>
                </TooltipContent>
              </Tooltip>
            </div>
            <Select 
              value={gameplan.defensiveAgg} 
              onValueChange={(val) => handleChange('defensiveAgg', val)}
            >
              <SelectTrigger 
                id={`ddl-def-agg-${coachId}`}
                className="bg-[#0a1929] border-[#2d4a6f] text-white text-xs h-8"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                {AGGRESSIVENESS_OPTIONS.map(opt => (
                  <SelectItem key={opt} value={opt} className="text-xs">{opt}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Coverage Scheme */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Label className="text-xs text-white">Coverage Scheme</Label>
              <Tooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-3 w-3 text-[#94a3b8] cursor-help" />
                </TooltipTrigger>
                <TooltipContent 
                  className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-xs"
                  id={`ddl-coverage-tt-${coachId}`}
                >
                  <p className="text-xs">
                    How you cover receivers. Man challenges routes; Zone guards space 
                    and deep shots; Hybrid mixes both.
                  </p>
                </TooltipContent>
              </Tooltip>
            </div>
            <Select 
              value={gameplan.coverage} 
              onValueChange={(val) => handleChange('coverage', val)}
            >
              <SelectTrigger 
                id={`ddl-coverage-${coachId}`}
                className="bg-[#0a1929] border-[#2d4a6f] text-white text-xs h-8"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                {COVERAGE_OPTIONS.map(opt => (
                  <SelectItem key={opt} value={opt} className="text-xs">{opt}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Blitz Strategy */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Label className="text-xs text-white">Blitz Strategy</Label>
              <Tooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-3 w-3 text-[#94a3b8] cursor-help" />
                </TooltipTrigger>
                <TooltipContent 
                  className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-xs"
                  id={`ddl-blitz-tt-${coachId}`}
                >
                  <p className="text-xs">
                    How often you bring extra rushers. Blitz Heavy hunts sacks but 
                    opens windows for screens and deep shots.
                  </p>
                </TooltipContent>
              </Tooltip>
            </div>
            <Select 
              value={gameplan.blitz} 
              onValueChange={(val) => handleChange('blitz', val)}
            >
              <SelectTrigger 
                id={`ddl-blitz-${coachId}`}
                className="bg-[#0a1929] border-[#2d4a6f] text-white text-xs h-8"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                {BLITZ_OPTIONS.map(opt => (
                  <SelectItem key={opt} value={opt} className="text-xs">{opt}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Red Zone Defense */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Label className="text-xs text-white">Red Zone Defense</Label>
              <Tooltip>
                <TooltipTrigger asChild>
                  <HelpCircle className="h-3 w-3 text-[#94a3b8] cursor-help" />
                </TooltipTrigger>
                <TooltipContent 
                  className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-xs"
                  id={`ddl-rz-def-tt-${coachId}`}
                >
                  <p className="text-xs">
                    Defend the red zone. Bend limits big plays; Run-Sellout plugs gaps; 
                    Pressure chases sacks/turnovers at higher risk.
                  </p>
                </TooltipContent>
              </Tooltip>
            </div>
            <Select 
              value={gameplan.rzDefense} 
              onValueChange={(val) => handleChange('rzDefense', val)}
            >
              <SelectTrigger 
                id={`ddl-rz-def-${coachId}`}
                className="bg-[#0a1929] border-[#2d4a6f] text-white text-xs h-8"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                {RZ_DEFENSE_OPTIONS.map(opt => (
                  <SelectItem key={opt} value={opt} className="text-xs">{opt}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <p className="text-xs text-[#94a3b8] italic">Saved per opponent</p>
        </div>
      </TooltipProvider>
    </div>
  );
}
