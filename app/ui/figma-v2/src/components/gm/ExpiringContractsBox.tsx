/**
 * Expiring Contracts Box - Data-bound spec
 * Shows players with expiring contracts with negotiate/trade/release actions
 */

import { useState, useEffect } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Skeleton } from '../ui/skeleton';
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../ui/alert-dialog';
import { Info } from 'lucide-react';
import { getExpiringContracts, getAllTeams, ExpiringContract } from '../../lib/mockGMApi';
import { ClickablePlayerName } from '../ui/ClickablePlayerName';
import { toast } from 'sonner@2.0.3';

export function ExpiringContractsBox() {
  const [selectedTeam, setSelectedTeam] = useState('New England Patriots');
  const [teams, setTeams] = useState<string[]>([]);
  const [contracts, setContracts] = useState<ExpiringContract[]>([]);
  const [loading, setLoading] = useState(true);
  const [releasePlayer, setReleasePlayer] = useState<ExpiringContract | null>(null);
  const [negotiatePlayer, setNegotiatePlayer] = useState<ExpiringContract | null>(null);

  useEffect(() => {
    loadTeams();
  }, []);

  useEffect(() => {
    if (selectedTeam) {
      loadContracts();
    }
  }, [selectedTeam]);

  const loadTeams = async () => {
    try {
      const teamList = await getAllTeams();
      // Put user team first, then alphabetical
      const userTeam = 'New England Patriots';
      const otherTeams = teamList.filter(t => t !== userTeam);
      setTeams([userTeam, ...otherTeams]);
    } catch (err) {
      console.error('Failed to load teams:', err);
    }
  };

  const loadContracts = async () => {
    setLoading(true);
    try {
      // Dev hook: GET /api/v1/contracts/expiring?team_id={teamId}&season={season}
      const data = await getExpiringContracts(selectedTeam);
      setContracts(data);
    } catch (err) {
      console.error('Failed to load expiring contracts:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleNegotiate = (contract: ExpiringContract) => {
    setNegotiatePlayer(contract);
  };

  const handleSubmitNegotiation = () => {
    if (!negotiatePlayer) return;
    
    // Dev hook: POST /api/v1/contracts/resign { season, team_id, player_id, years, aav }
    // Simulate success
    const total = negotiatePlayer.desiredLength * parseInt(negotiatePlayer.desiredAPY.replace(/[$M]/g, ''));
    toast.success(`Signed: ${negotiatePlayer.desiredLength}y / $${total}M`);
    setNegotiatePlayer(null);
    loadContracts(); // Refresh table
  };

  const handleTradeFor = (contract: ExpiringContract) => {
    // Dev hook: navigate to GM Trade screen with this player queued on target side
    // prefill /api/v1/trades/propose draft payload
    toast.info(`Trade feature: Opening trade screen with ${contract.name}...`);
  };

  const handleRelease = (contract: ExpiringContract) => {
    setReleasePlayer(contract);
  };

  const confirmRelease = () => {
    if (!releasePlayer) return;
    
    // Dev hook: call release endpoint then refresh table
    toast.success(`Released ${releasePlayer.name} to Free Agency`);
    setReleasePlayer(null);
    loadContracts(); // Refresh table
  };

  // Check if player is expensive (90th percentile for position - simplified)
  const isExpensive = (contract: ExpiringContract) => {
    const aav = parseInt(contract.desiredAPY.replace(/[$M]/g, ''));
    return aav >= 15; // Simplified threshold
  };

  // Check if player is team favorite (overall >= 90 or captain flag)
  const isTeamFavorite = (contract: ExpiringContract) => {
    return contract.overall >= 90;
  };

  return (
    <>
      <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
        {/* Header */}
        <div className="p-4 border-b border-[#2d4a6f]">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-white">Expiring Contracts</h3>
            <Select value={selectedTeam} onValueChange={setSelectedTeam}>
              <SelectTrigger 
                id="ddl-expiring-team"
                className="w-[250px] bg-[#0a1929] border-[#2d4a6f] text-white"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-h-[300px]">
                {teams.map((team) => (
                  <SelectItem 
                    key={team} 
                    value={team} 
                    className="hover:bg-[#2d4a6f] focus:bg-[#2d4a6f]"
                  >
                    {team}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-4 space-y-2">
              {[...Array(4)].map((_, i) => (
                <Skeleton 
                  key={i} 
                  id={`skeleton-expiring-${i}`}
                  className="h-11 bg-[#2d4a6f] animate-pulse" 
                />
              ))}
            </div>
          ) : contracts.length === 0 ? (
            <div className="text-center py-12 px-4">
              <h4 className="text-white mb-1">No expiring contracts</h4>
              <p className="text-[#94a3b8] text-sm">
                Try a different team from the dropdown.
              </p>
            </div>
          ) : (
            <table id="tbl-expiring" className="w-full">
              <thead className="bg-[#0a1929] sticky top-0 z-10">
                <tr className="border-b border-[#2d4a6f]">
                  <th id="col-player" className="px-4 py-3 text-left text-xs uppercase tracking-wide text-white whitespace-nowrap">
                    Player
                  </th>
                  <th id="col-pos" className="px-4 py-3 text-left text-xs uppercase tracking-wide text-white whitespace-nowrap">
                    POS
                  </th>
                  <th id="col-age" className="px-4 py-3 text-left text-xs uppercase tracking-wide text-white whitespace-nowrap">
                    Age
                  </th>
                  <th id="col-cap" className="px-4 py-3 text-left text-xs uppercase tracking-wide text-white whitespace-nowrap">
                    <div className="flex items-center gap-1">
                      Cap Hit
                      <TooltipProvider delayDuration={0}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Info className="h-3 w-3 text-[#94a3b8] cursor-help" aria-describedby="tt-cap" />
                          </TooltipTrigger>
                          <TooltipContent 
                            id="tt-cap"
                            className="bg-[#0a1929] border-[#2d4a6f] text-white"
                          >
                            <p>This season's cap charge for this player.</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                  </th>
                  <th id="col-ask-years" className="px-4 py-3 text-left text-xs uppercase tracking-wide text-white whitespace-nowrap">
                    Ask (Years)
                  </th>
                  <th id="col-ask-total" className="px-4 py-3 text-left text-xs uppercase tracking-wide text-white whitespace-nowrap">
                    <div className="flex items-center gap-1">
                      Ask (Total)
                      <TooltipProvider delayDuration={0}>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Info className="h-3 w-3 text-[#94a3b8] cursor-help" aria-describedby="tt-ask" />
                          </TooltipTrigger>
                          <TooltipContent 
                            id="tt-ask"
                            className="bg-[#0a1929] border-[#2d4a6f] text-white"
                          >
                            <p>Player's current asking price (Years × AAV). Meets threshold → instant accept.</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                  </th>
                  <th id="col-ask-aav" className="px-4 py-3 text-left text-xs uppercase tracking-wide text-white whitespace-nowrap">
                    Ask (AAV)
                  </th>
                  <th id="col-actions" className="px-4 py-3 text-left text-xs uppercase tracking-wide text-white whitespace-nowrap">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2d4a6f]">
                {contracts.map((contract) => (
                  <tr 
                    key={contract.playerId} 
                    id={`row-expiring-${contract.playerId}`}
                    className="hover:bg-[#2d4a6f]/30 h-11"
                  >
                    <td className="px-4 py-2 text-sm">
                      <ClickablePlayerName 
                        player={{
                          id: contract.playerId,
                          name: contract.name,
                          position: contract.position,
                          age: contract.age,
                          overall: contract.overall,
                        }}
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span id={`txt-player-${contract.playerId}`} className="text-white">
                              {contract.name}
                            </span>
                            {isExpensive(contract) && (
                              <span 
                                id={`badge-expensive-${contract.playerId}`}
                                className="px-1.5 py-0.5 text-[10px] rounded bg-red-500/20 text-red-300 uppercase"
                              >
                                Expensive
                              </span>
                            )}
                            {isTeamFavorite(contract) && (
                              <span 
                                id={`badge-favorite-${contract.playerId}`}
                                className="px-1.5 py-0.5 text-[10px] rounded bg-[#d4af37]/20 text-[#d4af37] uppercase"
                              >
                                Team Favorite
                              </span>
                            )}
                          </div>
                          <div id={`txt-pos-age-${contract.playerId}`} className="text-xs text-[#94a3b8]">
                            {contract.position} • {contract.age}
                          </div>
                        </div>
                      </ClickablePlayerName>
                    </td>
                    <td className="px-4 py-2 text-sm text-white">
                      <span id={`txt-pos-${contract.playerId}`}>{contract.position}</span>
                    </td>
                    <td className="px-4 py-2 text-sm text-white">
                      <span id={`txt-age-${contract.playerId}`}>{contract.age}</span>
                    </td>
                    <td className="px-4 py-2 text-sm text-white">
                      <span id={`txt-cap-${contract.playerId}`}>{contract.currentCapHit}</span>
                    </td>
                    <td className="px-4 py-2 text-sm text-white">
                      <span id={`txt-ask-years-${contract.playerId}`}>{contract.desiredLength}</span>
                    </td>
                    <td className="px-4 py-2 text-sm text-white">
                      <span id={`txt-ask-total-${contract.playerId}`}>{contract.desiredTotal}</span>
                    </td>
                    <td className="px-4 py-2 text-sm text-white">
                      <span id={`txt-ask-aav-${contract.playerId}`}>{contract.desiredAPY}</span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        <Button
                          id={`btn-negotiate-${contract.playerId}`}
                          onClick={() => handleNegotiate(contract)}
                          size="sm"
                          className="h-7 bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929] focus:ring-2 focus:ring-[#d4af37] focus:ring-offset-2 focus:ring-offset-[#1a2332]"
                        >
                          Negotiate
                        </Button>
                        <Button
                          id={`btn-tradefor-${contract.playerId}`}
                          onClick={() => handleTradeFor(contract)}
                          size="sm"
                          variant="outline"
                          className="h-7 bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]/50 focus:ring-2 focus:ring-[#2d4a6f] focus:ring-offset-2 focus:ring-offset-[#1a2332]"
                        >
                          Trade For
                        </Button>
                        <Button
                          id={`btn-release-${contract.playerId}`}
                          onClick={() => handleRelease(contract)}
                          size="sm"
                          variant="outline"
                          className="h-7 bg-transparent border-red-400/30 text-red-400 hover:bg-red-400/10 focus:ring-2 focus:ring-red-400 focus:ring-offset-2 focus:ring-offset-[#1a2332]"
                        >
                          Release
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-[#2d4a6f] bg-[#0a1929]">
          <p className="text-xs text-[#94a3b8]">
            Offers that meet threshold are accepted immediately.
          </p>
        </div>
      </div>

      {/* Release Confirmation Dialog */}
      <AlertDialog open={!!releasePlayer} onOpenChange={(open) => !open && setReleasePlayer(null)}>
        <AlertDialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
          <AlertDialogHeader>
            <AlertDialogTitle>Release {releasePlayer?.name}?</AlertDialogTitle>
            <AlertDialogDescription className="text-[#94a3b8]">
              This moves him to FA. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]/30">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={confirmRelease}
              className="bg-red-500 hover:bg-red-600 text-white"
            >
              Release Player
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Negotiate Modal (simplified - in real app this would be more complex) */}
      <AlertDialog open={!!negotiatePlayer} onOpenChange={(open) => !open && setNegotiatePlayer(null)}>
        <AlertDialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
          <AlertDialogHeader>
            <AlertDialogTitle>Negotiate with {negotiatePlayer?.name}</AlertDialogTitle>
            <AlertDialogDescription className="text-[#94a3b8]">
              Player is asking for {negotiatePlayer?.desiredLength} years at {negotiatePlayer?.desiredAPY}/year (Total: {negotiatePlayer?.desiredTotal})
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-4">
            <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
              <p className="text-sm text-[#94a3b8] mb-2">Current Ask:</p>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-xs text-[#94a3b8]">Years</p>
                  <p className="text-white">{negotiatePlayer?.desiredLength}</p>
                </div>
                <div>
                  <p className="text-xs text-[#94a3b8]">AAV</p>
                  <p className="text-white">{negotiatePlayer?.desiredAPY}</p>
                </div>
                <div>
                  <p className="text-xs text-[#94a3b8]">Total</p>
                  <p className="text-white">{negotiatePlayer?.desiredTotal}</p>
                </div>
              </div>
            </div>
            <p className="text-xs text-[#94a3b8] mt-3">
              💡 In a full implementation, you would see sliders to adjust the offer here.
            </p>
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]/30">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleSubmitNegotiation}
              className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
            >
              Accept Offer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
