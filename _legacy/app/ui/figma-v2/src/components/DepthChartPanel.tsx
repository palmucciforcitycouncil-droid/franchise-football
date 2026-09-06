import { useState } from 'react';
import { Button } from './ui/button';
import { Skeleton } from './ui/skeleton';
import { AlertCircle, AlertTriangle } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { DepthChartPayload, PlayerData, getPlayerById, POSITION_SLOTS } from '../lib/mockDepthChartApi';

interface DepthChartPanelProps {
  depthChart: DepthChartPayload | null;
  loading: boolean;
  onPlayerClick: (player: PlayerData) => void;
  onOpenAutoFill: () => void;
  hasUnsavedChanges: boolean;
  onSaveChanges: () => void;
  onRevert: () => void;
}

interface PositionBlock {
  title: string;
  positions: string[];
}

const POSITION_BLOCKS: PositionBlock[] = [
  {
    title: 'Offense - Skill',
    positions: ['QB', 'RB', 'WR', 'TE'],
  },
  {
    title: 'Offense - Line',
    positions: ['LT', 'LG', 'C', 'RG', 'RT'],
  },
  {
    title: 'Defense - Line',
    positions: ['DE-L', 'DT', 'DE-R'],
  },
  {
    title: 'Defense - Linebackers',
    positions: ['OLB-L', 'MLB', 'OLB-R'],
  },
  {
    title: 'Defense - Secondary',
    positions: ['CB', 'FS', 'SS'],
  },
  {
    title: 'Special Teams',
    positions: ['K', 'P'],
  },
];

export function DepthChartPanel({
  depthChart,
  loading,
  onPlayerClick,
  onOpenAutoFill,
  hasUnsavedChanges,
  onSaveChanges,
  onRevert,
}: DepthChartPanelProps) {
  const getAssignmentForSlot = (slot: string) => {
    return depthChart?.assignments.find(a => a.slot === slot);
  };

  const getPlayerForSlot = (slot: string): PlayerData | null => {
    const assignment = getAssignmentForSlot(slot);
    if (!assignment || !assignment.player_id) return null;
    return getPlayerById(assignment.player_id) || null;
  };

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'Active':
        return 'bg-green-500/20 text-green-400';
      case 'Doubtful':
        return 'bg-amber-500/20 text-amber-400';
      case 'OUT':
        return 'bg-red-500/20 text-red-400';
      case 'IR':
      case 'PUP':
        return 'bg-gray-500/20 text-gray-400';
      default:
        return 'bg-gray-500/20 text-gray-400';
    }
  };

  const renderPlayerRow = (slot: string, posGroup: string) => {
    const player = getPlayerForSlot(slot);
    const assignment = getAssignmentForSlot(slot);
    const hasCrossTrain = assignment?.notes.includes('xtrain:-2');

    if (!player) {
      return (
        <tr key={slot} className="border-b border-[#2d4a6f]/50 hover:bg-[#2d4a6f]/20">
          <td className="py-2.5 px-3 text-[#94a3b8]">{slot}</td>
          <td className="py-2.5 px-3 text-[#94a3b8] italic" colSpan={9}>
            Unfilled
          </td>
        </tr>
      );
    }

    return (
      <tr
        key={slot}
        className="border-b border-[#2d4a6f]/50 hover:bg-[#2d4a6f]/30 transition-colors cursor-pointer group"
        onClick={() => onPlayerClick(player)}
      >
        <td className="py-2.5 px-3 text-[#94a3b8]">{slot}</td>
        <td className="py-2.5 px-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-[#2d4a6f] flex items-center justify-center text-white text-xs flex-shrink-0">
              {player.jersey_number}
            </div>
            <span className="text-white truncate">
              {player.first_name} {player.last_name}
            </span>
            {hasCrossTrain && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                      X-train
                    </span>
                  </TooltipTrigger>
                  <TooltipContent className="bg-[#0a1929] border-[#2d4a6f] text-white">
                    Cross-trained from {player.position} (-2 OVR)
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
        </td>
        <td className="py-2.5 px-3 text-[#94a3b8]">{player.position}</td>
        <td className="py-2.5 px-3">
          <span className="inline-block px-2 py-1 rounded bg-[#d4af37]/20 text-[#d4af37] border border-[#d4af37]/30 tabular-nums">
            {assignment?.ovr_at_slot || player.ratings.ovr}
          </span>
        </td>
        <td className="py-2.5 px-3 text-white tabular-nums">{player.ratings.spd}</td>
        <td className="py-2.5 px-3 text-white tabular-nums">{player.ratings.str}</td>
        <td className="py-2.5 px-3 text-white tabular-nums">{player.ratings.agi}</td>
        <td className="py-2.5 px-3 text-white tabular-nums">{player.ratings.awr}</td>
        <td className="py-2.5 px-3">
          <div className="flex items-center gap-1">
            <span className="text-white tabular-nums">{player.ratings.sta}</span>
            {player.ratings.sta < 50 && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                  </TooltipTrigger>
                  <TooltipContent className="bg-[#0a1929] border-[#2d4a6f] text-white">
                    Low stamina (&lt;50) — reduced late-game performance
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
        </td>
        <td className="py-2.5 px-3">
          <div className="flex items-center gap-1">
            <span className={`inline-block px-2 py-0.5 rounded text-xs ${getHealthColor(player.status)}`}>
              {player.status}
            </span>
            {(player.status === 'OUT' || player.status === 'Doubtful') && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <AlertCircle className="h-3.5 w-3.5 text-red-400" />
                  </TooltipTrigger>
                  <TooltipContent className="bg-[#0a1929] border-[#2d4a6f] text-white">
                    Injury risk in lineup
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
        </td>
      </tr>
    );
  };

  const renderLoadingRow = (index: number) => (
    <tr key={`loading-${index}`} className="border-b border-[#2d4a6f]/50">
      <td className="py-2.5 px-3">
        <Skeleton className="h-5 w-12 bg-[#2d4a6f]" />
      </td>
      <td className="py-2.5 px-3">
        <Skeleton className="h-7 w-32 bg-[#2d4a6f]" />
      </td>
      <td className="py-2.5 px-3">
        <Skeleton className="h-5 w-8 bg-[#2d4a6f]" />
      </td>
      <td className="py-2.5 px-3">
        <Skeleton className="h-6 w-10 bg-[#2d4a6f]" />
      </td>
      <td className="py-2.5 px-3">
        <Skeleton className="h-5 w-8 bg-[#2d4a6f]" />
      </td>
      <td className="py-2.5 px-3">
        <Skeleton className="h-5 w-8 bg-[#2d4a6f]" />
      </td>
      <td className="py-2.5 px-3">
        <Skeleton className="h-5 w-8 bg-[#2d4a6f]" />
      </td>
      <td className="py-2.5 px-3">
        <Skeleton className="h-5 w-8 bg-[#2d4a6f]" />
      </td>
      <td className="py-2.5 px-3">
        <Skeleton className="h-5 w-8 bg-[#2d4a6f]" />
      </td>
      <td className="py-2.5 px-3">
        <Skeleton className="h-5 w-16 bg-[#2d4a6f]" />
      </td>
    </tr>
  );

  const isEmpty = !loading && (!depthChart || depthChart.assignments.every(a => !a.player_id));

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f]">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-white mb-1">Depth Chart</h3>
            {depthChart && depthChart.warnings.length > 0 && (
              <p className="text-sm text-amber-400">
                {depthChart.warnings.length} warning{depthChart.warnings.length !== 1 ? 's' : ''}
              </p>
            )}
          </div>
          <Button
            onClick={onOpenAutoFill}
            disabled={loading}
            className="bg-[#d4af37] hover:bg-[#b8941f] text-[#0a1929]"
          >
            Auto-Fill Depth Chart
          </Button>
        </div>
        
        {/* Warnings */}
        {depthChart && depthChart.warnings.length > 0 && (
          <div className="mt-3 p-3 rounded bg-amber-500/10 border border-amber-500/30">
            <p className="text-sm text-amber-400 mb-2">Warnings:</p>
            <ul className="text-sm text-amber-300 space-y-1">
              {depthChart.warnings.slice(0, 5).map((warning, i) => (
                <li key={i} className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  <span>{warning}</span>
                </li>
              ))}
              {depthChart.warnings.length > 5 && (
                <li className="text-amber-400 italic">
                  +{depthChart.warnings.length - 5} more warnings
                </li>
              )}
            </ul>
          </div>
        )}
      </div>

      {/* Empty State */}
      {isEmpty && (
        <div className="py-16 text-center">
          <div className="text-[#94a3b8] space-y-2">
            <p>No depth chart yet.</p>
            <p className="text-sm">Click Auto-Fill to generate one.</p>
          </div>
        </div>
      )}

      {/* Table */}
      {!isEmpty && (
        <div className="overflow-auto max-h-[600px]">
          <table className="w-full text-sm border-collapse">
            <thead className="sticky top-0 bg-[#1a2332] z-10 shadow-[0_2px_4px_rgba(0,0,0,0.3)]">
              <tr className="border-b border-[#2d4a6f]">
                <th className="text-left py-3 px-3 text-[#94a3b8] min-w-[80px]">Slot</th>
                <th className="text-left py-3 px-3 text-[#94a3b8] min-w-[180px]">Player</th>
                <th className="text-left py-3 px-3 text-[#94a3b8] min-w-[60px]">POS</th>
                <th className="text-left py-3 px-3 text-[#94a3b8] min-w-[70px]">
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="cursor-help">OVR</span>
                      </TooltipTrigger>
                      <TooltipContent className="bg-[#0a1929] border-[#2d4a6f] text-white">
                        Overall (composite)
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </th>
                <th className="text-left py-3 px-3 text-[#94a3b8] min-w-[60px]">SPD</th>
                <th className="text-left py-3 px-3 text-[#94a3b8] min-w-[60px]">STR</th>
                <th className="text-left py-3 px-3 text-[#94a3b8] min-w-[60px]">AGI</th>
                <th className="text-left py-3 px-3 text-[#94a3b8] min-w-[60px]">AWR</th>
                <th className="text-left py-3 px-3 text-[#94a3b8] min-w-[60px]">STA</th>
                <th className="text-left py-3 px-3 text-[#94a3b8] min-w-[100px]">Status</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 12 }).map((_, i) => renderLoadingRow(i))
              ) : (
                POSITION_BLOCKS.map((block, blockIdx) => (
                  <tr key={`block-${blockIdx}`}>
                    <td colSpan={10}>
                      {/* Block Header */}
                      <div className="bg-[#0a1929] py-2 px-3 border-y border-[#2d4a6f] sticky top-[41px] z-[9]">
                        <h4 className="text-[#d4af37]">{block.title}</h4>
                      </div>
                      {/* Block Rows */}
                      <table className="w-full">
                        <tbody>
                          {block.positions.map(posGroup => {
                            const slots = POSITION_SLOTS[posGroup as keyof typeof POSITION_SLOTS];
                            return slots?.map(slot => renderPlayerRow(slot, posGroup));
                          })}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Sticky Footer Save Bar */}
      {hasUnsavedChanges && (
        <div className="sticky bottom-0 bg-[#0a1929] border-t border-[#2d4a6f] p-4 flex items-center justify-between shadow-[0_-2px_8px_rgba(0,0,0,0.3)]">
          <div className="text-[#94a3b8]">
            <span className="text-[#d4af37]">Unsaved changes</span>
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              onClick={onRevert}
              className="text-[#94a3b8] hover:text-white hover:bg-[#2d4a6f]"
            >
              Revert
            </Button>
            <Button
              onClick={onSaveChanges}
              className="bg-[#d4af37] hover:bg-[#b8941f] text-[#0a1929]"
            >
              Save Changes
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
