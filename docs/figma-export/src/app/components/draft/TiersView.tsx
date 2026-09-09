/**
 * Tiers View Component
 * Tabs by position with collapsible tiers
 */

import { useState, useEffect } from 'react';
import { DraftProspect, getProspectsByTier } from '../../lib/mockDraftApi';
import { Badge } from '../ui/badge';
import { Skeleton } from '../ui/skeleton';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '../ui/collapsible';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { ClickablePlayerName } from '../ui/ClickablePlayerName';

interface TiersViewProps {
  onProspectClick?: (prospect: DraftProspect) => void;
}

export function TiersView({ onProspectClick }: TiersViewProps) {
  const [activePosition, setActivePosition] = useState('ALL');
  const [tiers, setTiers] = useState<{ tier: number; prospects: DraftProspect[] }[]>([]);
  const [loading, setLoading] = useState(true);
  const [openTiers, setOpenTiers] = useState<Set<number>>(new Set([1, 2]));

  const positions = ['ALL', 'QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S', 'K'];

  useEffect(() => {
    loadTiers();
  }, [activePosition]);

  const loadTiers = async () => {
    setLoading(true);
    try {
      const data = await getProspectsByTier(activePosition);
      setTiers(data);
    } catch (error) {
      console.error('Failed to load tiers:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleTier = (tier: number) => {
    const newOpen = new Set(openTiers);
    if (newOpen.has(tier)) {
      newOpen.delete(tier);
    } else {
      newOpen.add(tier);
    }
    setOpenTiers(newOpen);
  };

  const getTierLabel = (tier: number) => {
    switch (tier) {
      case 1: return 'Elite';
      case 2: return 'High Quality';
      case 3: return 'Solid Starter';
      case 4: return 'Developmental';
      case 5: return 'Depth/Project';
      default: return `Tier ${tier}`;
    }
  };

  const getTierColor = (tier: number) => {
    switch (tier) {
      case 1: return 'border-[#d4af37] bg-[#d4af37]/10';
      case 2: return 'border-[#3498db] bg-[#3498db]/10';
      case 3: return 'border-[#27ae60] bg-[#27ae60]/10';
      case 4: return 'border-[#f39c12] bg-[#f39c12]/10';
      case 5: return 'border-[#94a3b8] bg-[#94a3b8]/10';
      default: return 'border-[#1F2A35] bg-[#1F2A35]/10';
    }
  };

  return (
    <div className="space-y-6">
      {/* Position Tabs */}
      <div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] p-6">
        <Tabs value={activePosition} onValueChange={setActivePosition}>
          <TabsList className="bg-[#0B0F14] border border-[#1F2A35] p-1">
            {positions.map((pos) => (
              <TabsTrigger
                key={pos}
                value={pos}
                className="data-[state=active]:bg-[#1e3a5f] data-[state=active]:text-white text-[#94a3b8]"
              >
                {pos}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* Tiers */}
      {loading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-32 bg-[#11161C]" />
          ))}
        </div>
      ) : tiers.length === 0 ? (
        <div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] p-12 text-center">
          <p className="text-[#94a3b8]">No prospects found for this position</p>
        </div>
      ) : (
        <div className="space-y-4">
          {tiers.map(({ tier, prospects }) => (
            <Collapsible
              key={tier}
              open={openTiers.has(tier)}
              onOpenChange={() => toggleTier(tier)}
            >
              <div className={`bg-[#11161C] border-2 rounded-2xl overflow-hidden ${getTierColor(tier)}`}>
                <CollapsibleTrigger className="w-full p-6 flex items-center justify-between hover:bg-[#1a2332] transition-colors">
                  <div className="flex items-center gap-4">
                    {openTiers.has(tier) ? (
                      <ChevronDown className="w-5 h-5 text-[#94a3b8]" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-[#94a3b8]" />
                    )}
                    <div className="text-left">
                      <h3 className="text-white">Tier {tier}: {getTierLabel(tier)}</h3>
                      <p className="text-[#94a3b8] text-sm">{prospects.length} prospects</p>
                    </div>
                  </div>
                  <Badge variant="outline" className="border-[#2d4a6f] text-[#94a3b8]">
                    {prospects.filter(p => !p.drafted).length} available
                  </Badge>
                </CollapsibleTrigger>

                <CollapsibleContent>
                  <div className="p-6 pt-0 border-t border-[#1F2A35]">
                    <div className="flex flex-wrap gap-3">
                      {prospects.map((prospect) => (
                        <div
                          key={prospect.prospect_id}
                          onClick={() => onProspectClick?.(prospect)}
                          className={`flex-shrink-0 bg-[#0B0F14] border rounded-lg p-4 hover:bg-[#1a2332] transition-colors cursor-pointer ${
                            prospect.drafted ? 'border-[#1F2A35] opacity-60' : 'border-[#2d4a6f]'
                          }`}
                          style={{ width: 'calc(25% - 0.75rem)' }}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1 min-w-0">
                              <ClickablePlayerName player={prospect} className="text-white text-sm truncate block">
                                {prospect.name}
                              </ClickablePlayerName>
                              <div className="text-[#94a3b8] text-xs">{prospect.college}</div>
                            </div>
                            <Badge
                              variant="outline"
                              className="ml-2 border-[#2d4a6f] text-[#94a3b8] flex-shrink-0"
                            >
                              {prospect.position}
                            </Badge>
                          </div>
                          
                          <div className="space-y-1.5 mb-3">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-[#94a3b8]">Overall</span>
                              <span className="text-white">{prospect.overall}</span>
                            </div>
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-[#94a3b8]">Potential</span>
                              <span className="text-white">{prospect.potential}</span>
                            </div>
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-[#94a3b8]">Board</span>
                              <span className="text-white">{prospect.board_score}</span>
                            </div>
                          </div>

                          {prospect.drafted ? (
                            <Badge className="w-full justify-center bg-[#e74c3c]/20 text-[#e74c3c] border border-[#e74c3c]/30 text-xs">
                              Drafted - Rd {prospect.draft_round}
                            </Badge>
                          ) : (
                            <Badge className="w-full justify-center bg-[#27ae60]/20 text-[#27ae60] border border-[#27ae60]/30 text-xs">
                              Available
                            </Badge>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </CollapsibleContent>
              </div>
            </Collapsible>
          ))}
        </div>
      )}
    </div>
  );
}
