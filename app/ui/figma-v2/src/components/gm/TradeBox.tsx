import { useState, useEffect } from 'react';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { X, Plus, ArrowRight, AlertCircle } from 'lucide-react';
import { 
  proposeTrade, 
  getTradeValuePreview,
  getAllTeams as getAllTeamsAPI,
  getTeamRoster,
  getTeamPicks,
  getCurrentSeason,
  TradeAsset
} from '../../lib/tradeApi';
import type { Team, Player as APIPlayer, DraftPick as APIDraftPick } from '../../lib/tradeApi';
import { toast } from 'sonner@2.0.3';

export function TradeBox() {
  const [teams, setTeams] = useState<string[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string>('');
  const [offeringAssets, setOfferingAssets] = useState<TradeAsset[]>([]);
  const [receivingAssets, setReceivingAssets] = useState<TradeAsset[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [showAddOffering, setShowAddOffering] = useState(false);
  const [showAddReceiving, setShowAddReceiving] = useState(false);
  const [offeringFilter, setOfferingFilter] = useState<string>('ALL');
  const [receivingFilter, setReceivingFilter] = useState<string>('ALL');

  // New state for API data
  const [currentSeason, setCurrentSeason] = useState<number>(2025);
  const [userTeamId, setUserTeamId] = useState<number>(1);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
  const [teamMap, setTeamMap] = useState<Team[]>([]);
  const [userPlayers, setUserPlayers] = useState<APIPlayer[]>([]);
  const [userPicks, setUserPicks] = useState<APIDraftPick[]>([]);
  const [otherTeamPlayers, setOtherTeamPlayers] = useState<APIPlayer[]>([]);
  const [otherTeamPicks, setOtherTeamPicks] = useState<APIDraftPick[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTeams();
  }, []);

  const loadTeams = async () => {
    setLoading(true);
    try {
      const context = await getCurrentSeason();
      setCurrentSeason(context.season);
      setUserTeamId(context.current_user_team_id);
      
      const teamList = await getAllTeamsAPI();
      setTeamMap(teamList);
      // Filter out current user's team
      const otherTeams = teamList
        .filter(t => t.id !== context.current_user_team_id)
        .map(t => t.name);
      setTeams(otherTeams);
      
      // Load user's roster and picks
      const [roster, picks] = await Promise.all([
        getTeamRoster(context.current_user_team_id, context.season),
        getTeamPicks(context.current_user_team_id, context.season)
      ]);
      setUserPlayers(roster);
      setUserPicks(picks);
    } catch (err) {
      console.error('Failed to load teams:', err);
      toast.error('Failed to load team data');
    } finally {
      setLoading(false);
    }
  };

  const handleTeamChange = async (teamName: string) => {
    setSelectedTeam(teamName);
    const team = teamMap.find(t => t.name === teamName);
    if (team) {
      setSelectedTeamId(team.id);
      setLoading(true);
      
      try {
        const [roster, picks] = await Promise.all([
          getTeamRoster(team.id, currentSeason),
          getTeamPicks(team.id, currentSeason)
        ]);
        setOtherTeamPlayers(roster);
        setOtherTeamPicks(picks);
      } catch (err) {
        console.error('Failed to load team data:', err);
        toast.error('Failed to load team roster');
      } finally {
        setLoading(false);
      }
    }
  };

  const addOfferingAsset = (type: 'player' | 'pick', item: any) => {
    if (type === 'player') {
      setOfferingAssets([...offeringAssets, {
        type: 'player',
        id: item.id,
        name: item.name,
        position: item.position,
        overall: item.overall
      }]);
    } else {
      setOfferingAssets([...offeringAssets, {
        type: 'pick',
        id: item.id,
        name: `${item.year} Round ${item.round}${item.pickNumber ? ` (Pick ${item.pickNumber})` : ''}`,
        year: item.year,
        round: item.round,
        pickNumber: item.pickNumber
      }]);
    }
    setShowAddOffering(false);
  };

  const addReceivingAsset = (type: 'player' | 'pick', item: any) => {
    if (type === 'player') {
      setReceivingAssets([...receivingAssets, {
        type: 'player',
        id: item.id,
        name: item.name,
        position: item.position,
        overall: item.overall
      }]);
    } else {
      setReceivingAssets([...receivingAssets, {
        type: 'pick',
        id: item.id,
        name: `${item.year} Round ${item.round}${item.pickNumber ? ` (Pick ${item.pickNumber})` : ''}`,
        year: item.year,
        round: item.round,
        pickNumber: item.pickNumber
      }]);
    }
    setShowAddReceiving(false);
  };

  const removeOfferingAsset = (id: string) => {
    setOfferingAssets(offeringAssets.filter(a => a.id !== id));
  };

  const removeReceivingAsset = (id: string) => {
    setReceivingAssets(receivingAssets.filter(a => a.id !== id));
  };

  const handleSubmitTrade = async () => {
    if (!selectedTeam) {
      toast.error('Please select a team to trade with');
      return;
    }
    if (offeringAssets.length === 0 || receivingAssets.length === 0) {
      toast.error('Please add assets to both sides of the trade');
      return;
    }

    setSubmitting(true);
    try {
      const offer: TradeOffer = {
        teamOffering: 'New England Patriots',
        teamReceiving: selectedTeam,
        offeringAssets,
        receivingAssets
      };

      const response = await submitTradeOffer(offer);
      
      if (response.accepted) {
        toast.success(response.message);
        // Clear the trade
        setOfferingAssets([]);
        setReceivingAssets([]);
        setSelectedTeam('');
      } else {
        toast.error(response.message);
        if (response.counterOffer) {
          // Add counter offer to the list with the original offer
          setCounterOffers([...counterOffers, { original: offer, counter: response.counterOffer }]);
          toast.info('Counter-offer received! Check below to review.');
        }
        // Clear the trade form
        setOfferingAssets([]);
        setReceivingAssets([]);
        setSelectedTeam('');
      }
    } catch (err) {
      console.error('Failed to submit trade:', err);
      toast.error('Failed to submit trade offer');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAcceptCounter = (counterOffer: TradeOffer, index: number) => {
    toast.success(`Trade accepted! ${counterOffer.teamOffering} has agreed to the deal.`);
    // Remove the counter offer from the list
    setCounterOffers(counterOffers.filter((_, i) => i !== index));
  };

  const handleRejectCounter = (index: number) => {
    toast.info('Counter-offer rejected');
    setCounterOffers(counterOffers.filter((_, i) => i !== index));
  };

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] h-full">
      <div className="p-4 border-b border-[#2d4a6f]">
        <h3 className="text-white mb-3">Trade Proposal</h3>
        <Select value={selectedTeam} onValueChange={handleTeamChange}>
          <SelectTrigger className="w-full bg-[#0a1929] border-[#2d4a6f] text-white">
            <SelectValue placeholder="Select team to trade with..." />
          </SelectTrigger>
          <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-h-[300px]">
            {teams.map((team) => (
              <SelectItem key={team} value={team} className="hover:bg-[#2d4a6f]">
                {team}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="p-4 space-y-4">
        {/* Offering Section */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-white text-sm">You Offer</h4>
            {!showAddOffering && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowAddOffering(true)}
                className="h-7 text-xs bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
              >
                <Plus className="h-3 w-3 mr-1" />
                Add
              </Button>
            )}
          </div>

          {showAddOffering && (
            <div className="bg-[#0a1929] p-3 rounded border border-[#d4af37] mb-2">
              <div className="flex items-center justify-between mb-2">
                <span className="text-white text-sm">Add Asset</span>
                <button onClick={() => setShowAddOffering(false)}>
                  <X className="h-4 w-4 text-[#94a3b8]" />
                </button>
              </div>
              
              {/* Filter Dropdown */}
              <div className="mb-2">
                <Select value={offeringFilter} onValueChange={setOfferingFilter}>
                  <SelectTrigger className="w-full bg-[#1a2332] border-[#2d4a6f] text-white h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                    <SelectItem value="ALL" className="text-xs">All Players & Picks</SelectItem>
                    <SelectItem value="PICKS" className="text-xs">Draft Picks Only</SelectItem>
                    <SelectItem value="QB" className="text-xs">QB</SelectItem>
                    <SelectItem value="RB" className="text-xs">RB</SelectItem>
                    <SelectItem value="WR" className="text-xs">WR</SelectItem>
                    <SelectItem value="TE" className="text-xs">TE</SelectItem>
                    <SelectItem value="OL" className="text-xs">OL</SelectItem>
                    <SelectItem value="DL" className="text-xs">DL</SelectItem>
                    <SelectItem value="LB" className="text-xs">LB</SelectItem>
                    <SelectItem value="CB" className="text-xs">CB</SelectItem>
                    <SelectItem value="S" className="text-xs">S</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {/* Players */}
                {offeringFilter !== 'PICKS' && (
                  <div>
                    {userPlayers
                      .filter(player => offeringFilter === 'ALL' || player.position === offeringFilter)
                      .map(player => (
                        <button
                          key={player.id}
                          onClick={() => addOfferingAsset('player', player)}
                          disabled={offeringAssets.some(a => a.id === String(player.id))}
                          className="w-full text-left px-2 py-1.5 rounded bg-[#1a2332] hover:bg-[#2d4a6f] text-white text-xs disabled:opacity-50 disabled:cursor-not-allowed mb-1"
                        >
                          <div className="flex items-center gap-2">
                            <div className={`px-1.5 py-0.5 rounded text-xs ${
                              player.overall >= 90 ? 'bg-green-500/20 text-green-300' :
                              player.overall >= 85 ? 'bg-blue-500/20 text-blue-300' :
                              'bg-gray-500/20 text-gray-300'
                            }`}>
                              {player.overall}
                            </div>
                            <span>{player.name}</span>
                            <span className="text-[#94a3b8]">{player.position}</span>
                          </div>
                        </button>
                      ))}
                  </div>
                )}
                
                {/* Draft Picks */}
                {(offeringFilter === 'ALL' || offeringFilter === 'PICKS') && (
                  <div>
                    {offeringFilter === 'ALL' && userPlayers.filter(p => offeringFilter === 'ALL' || p.position === offeringFilter).length > 0 && (
                      <div className="text-xs text-[#94a3b8] mb-1 mt-2">Draft Picks</div>
                    )}
                    {userPicks.map(pick => (
                      <button
                        key={`${pick.round}-${pick.slot}`}
                        onClick={() => addOfferingAsset('pick', pick)}
                        disabled={offeringAssets.some(a => a.id === `pick-${pick.round}-${pick.slot}`)}
                        className="w-full text-left px-2 py-1.5 rounded bg-[#1a2332] hover:bg-[#2d4a6f] text-white text-xs disabled:opacity-50 disabled:cursor-not-allowed mb-1"
                      >
                        {pick.year} Round {pick.round} (Pick {pick.slot})
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="space-y-2 min-h-[120px] bg-[#0a1929] p-3 rounded border border-[#2d4a6f]">
            {offeringAssets.length === 0 ? (
              <div className="text-center py-8 text-[#94a3b8] text-sm">
                No assets added
              </div>
            ) : (
              offeringAssets.map(asset => (
                <div key={asset.id} className="flex items-center justify-between bg-[#1a2332] p-2 rounded">
                  <div className="flex items-center gap-2">
                    {asset.type === 'player' ? (
                      <>
                        <div className={`px-2 py-0.5 rounded text-xs ${
                          asset.overall! >= 85 ? 'bg-green-500/20 text-green-300' :
                          'bg-blue-500/20 text-blue-300'
                        }`}>
                          {asset.overall}
                        </div>
                        <span className="text-white text-sm">{asset.name}</span>
                        <span className="text-[#94a3b8] text-xs">{asset.position}</span>
                      </>
                    ) : (
                      <span className="text-white text-sm">{asset.name}</span>
                    )}
                  </div>
                  <button onClick={() => removeOfferingAsset(asset.id)}>
                    <X className="h-4 w-4 text-[#94a3b8] hover:text-white" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Arrow Divider */}
        <div className="flex items-center justify-center">
          <div className="w-8 h-8 rounded-full bg-[#d4af37] flex items-center justify-center">
            <ArrowRight className="h-4 w-4 text-[#0a1929]" />
          </div>
        </div>

        {/* Receiving Section */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-white text-sm">You Receive</h4>
            {!showAddReceiving && selectedTeam && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowAddReceiving(true)}
                className="h-7 text-xs bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
              >
                <Plus className="h-3 w-3 mr-1" />
                Add
              </Button>
            )}
          </div>

          {!selectedTeam && (
            <div className="bg-[#991b1b]/20 border border-[#dc2626] rounded p-3 mb-2">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-[#dc2626] mt-0.5" />
                <div className="text-xs text-[#dc2626]">
                  Select a team to trade with first
                </div>
              </div>
            </div>
          )}

          {showAddReceiving && selectedTeam && (
            <div className="bg-[#0a1929] p-3 rounded border border-[#d4af37] mb-2">
              <div className="flex items-center justify-between mb-2">
                <span className="text-white text-sm">Add Asset</span>
                <button onClick={() => setShowAddReceiving(false)}>
                  <X className="h-4 w-4 text-[#94a3b8]" />
                </button>
              </div>
              
              {/* Filter Dropdown */}
              <div className="mb-2">
                <Select value={receivingFilter} onValueChange={setReceivingFilter}>
                  <SelectTrigger className="w-full bg-[#1a2332] border-[#2d4a6f] text-white h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                    <SelectItem value="ALL" className="text-xs">All Players & Picks</SelectItem>
                    <SelectItem value="PICKS" className="text-xs">Draft Picks Only</SelectItem>
                    <SelectItem value="QB" className="text-xs">QB</SelectItem>
                    <SelectItem value="RB" className="text-xs">RB</SelectItem>
                    <SelectItem value="WR" className="text-xs">WR</SelectItem>
                    <SelectItem value="TE" className="text-xs">TE</SelectItem>
                    <SelectItem value="OL" className="text-xs">OL</SelectItem>
                    <SelectItem value="DL" className="text-xs">DL</SelectItem>
                    <SelectItem value="LB" className="text-xs">LB</SelectItem>
                    <SelectItem value="CB" className="text-xs">CB</SelectItem>
                    <SelectItem value="S" className="text-xs">S</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {/* Players */}
                {receivingFilter !== 'PICKS' && (
                  <div>
                    {otherTeamPlayers
                      .filter(player => receivingFilter === 'ALL' || player.position === receivingFilter)
                      .map(player => (
                        <button
                          key={player.id}
                          onClick={() => addReceivingAsset('player', player)}
                          disabled={receivingAssets.some(a => a.id === String(player.id))}
                          className="w-full text-left px-2 py-1.5 rounded bg-[#1a2332] hover:bg-[#2d4a6f] text-white text-xs disabled:opacity-50 disabled:cursor-not-allowed mb-1"
                        >
                          <div className="flex items-center gap-2">
                            <div className={`px-1.5 py-0.5 rounded text-xs ${
                              player.overall >= 90 ? 'bg-green-500/20 text-green-300' :
                              player.overall >= 85 ? 'bg-blue-500/20 text-blue-300' :
                              'bg-gray-500/20 text-gray-300'
                            }`}>
                              {player.overall}
                            </div>
                            <span>{player.name}</span>
                            <span className="text-[#94a3b8]">{player.position}</span>
                          </div>
                        </button>
                      ))}
                  </div>
                )}
                
                {/* Draft Picks */}
                {(receivingFilter === 'ALL' || receivingFilter === 'PICKS') && (
                  <div>
                    {receivingFilter === 'ALL' && otherTeamPlayers.filter(p => receivingFilter === 'ALL' || p.position === receivingFilter).length > 0 && (
                      <div className="text-xs text-[#94a3b8] mb-1 mt-2">Draft Picks</div>
                    )}
                    {otherTeamPicks.map(pick => (
                      <button
                        key={`${pick.round}-${pick.slot}`}
                        onClick={() => addReceivingAsset('pick', pick)}
                        disabled={receivingAssets.some(a => a.id === `pick-${pick.round}-${pick.slot}`)}
                        className="w-full text-left px-2 py-1.5 rounded bg-[#1a2332] hover:bg-[#2d4a6f] text-white text-xs disabled:opacity-50 disabled:cursor-not-allowed mb-1"
                      >
                        {pick.year} Round {pick.round} (Pick {pick.slot})
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="space-y-2 min-h-[120px] bg-[#0a1929] p-3 rounded border border-[#2d4a6f]">
            {receivingAssets.length === 0 ? (
              <div className="text-center py-8 text-[#94a3b8] text-sm">
                No assets added
              </div>
            ) : (
              receivingAssets.map(asset => (
                <div key={asset.id} className="flex items-center justify-between bg-[#1a2332] p-2 rounded">
                  <div className="flex items-center gap-2">
                    {asset.type === 'player' ? (
                      <>
                        <div className={`px-2 py-0.5 rounded text-xs ${
                          asset.overall! >= 90 ? 'bg-green-500/20 text-green-300' :
                          asset.overall! >= 85 ? 'bg-blue-500/20 text-blue-300' :
                          'bg-gray-500/20 text-gray-300'
                        }`}>
                          {asset.overall}
                        </div>
                        <span className="text-white text-sm">{asset.name}</span>
                        <span className="text-[#94a3b8] text-xs">{asset.position}</span>
                      </>
                    ) : (
                      <span className="text-white text-sm">{asset.name}</span>
                    )}
                  </div>
                  <button onClick={() => removeReceivingAsset(asset.id)}>
                    <X className="h-4 w-4 text-[#94a3b8] hover:text-white" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Submit Button */}
        <Button
          onClick={handleSubmitTrade}
          disabled={!selectedTeam || offeringAssets.length === 0 || receivingAssets.length === 0 || submitting}
          className="w-full bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
        >
          {submitting ? 'Submitting...' : 'Submit Trade Offer'}
        </Button>

        {/* Counter Offers Section */}
        {counterOffers.length > 0 && (
          <div className="mt-6 pt-6 border-t border-[#2d4a6f]">
            <h4 className="text-white text-sm mb-3">
              Counter Offers ({counterOffers.length})
            </h4>
            <div className="space-y-4">
              {counterOffers.map(({ original, counter }, index) => (
                <div key={index} className="bg-[#0a1929] p-3 rounded border border-[#d4af37]">
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-white text-sm">{counter.teamOffering}</div>
                    <div className="text-xs text-[#94a3b8]">Original Offer</div>
                  </div>

                  {/* Your Original Offer */}
                  <div className="mb-3 pb-3 border-b border-[#2d4a6f]">
                    <div className="text-xs text-[#94a3b8] mb-2">Your Original Offer:</div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-xs text-[#94a3b8] mb-1">You Offered:</div>
                        <div className="space-y-1">
                          {original.offeringAssets.map(asset => (
                            <div key={asset.id} className="flex items-center gap-2 bg-[#1a2332] p-1.5 rounded text-xs">
                              {asset.type === 'player' ? (
                                <>
                                  <div className={`px-1.5 py-0.5 rounded text-xs ${
                                    asset.overall! >= 90 ? 'bg-green-500/20 text-green-300' :
                                    asset.overall! >= 85 ? 'bg-blue-500/20 text-blue-300' :
                                    'bg-gray-500/20 text-gray-300'
                                  }`}>
                                    {asset.overall}
                                  </div>
                                  <span className="text-white">{asset.name}</span>
                                  <span className="text-[#94a3b8]">{asset.position}</span>
                                </>
                              ) : (
                                <span className="text-white">{asset.name}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-[#94a3b8] mb-1">You Requested:</div>
                        <div className="space-y-1">
                          {original.receivingAssets.map(asset => (
                            <div key={asset.id} className="flex items-center gap-2 bg-[#1a2332] p-1.5 rounded text-xs">
                              {asset.type === 'player' ? (
                                <>
                                  <div className={`px-1.5 py-0.5 rounded text-xs ${
                                    asset.overall! >= 90 ? 'bg-green-500/20 text-green-300' :
                                    asset.overall! >= 85 ? 'bg-blue-500/20 text-blue-300' :
                                    'bg-gray-500/20 text-gray-300'
                                  }`}>
                                    {asset.overall}
                                  </div>
                                  <span className="text-white">{asset.name}</span>
                                  <span className="text-[#94a3b8]">{asset.position}</span>
                                </>
                              ) : (
                                <span className="text-white">{asset.name}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Their Counter Offer */}
                  <div className="mb-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-xs text-[#d4af37]">Their Counter Proposal:</div>
                      <div className="text-xs text-[#d4af37]">Counter Offer</div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-xs text-[#94a3b8] mb-1">They Offer:</div>
                        <div className="space-y-1">
                          {counter.offeringAssets.map(asset => (
                            <div key={asset.id} className="flex items-center gap-2 bg-[#1a2332] p-1.5 rounded text-xs">
                              {asset.type === 'player' ? (
                                <>
                                  <div className={`px-1.5 py-0.5 rounded text-xs ${
                                    asset.overall! >= 90 ? 'bg-green-500/20 text-green-300' :
                                    asset.overall! >= 85 ? 'bg-blue-500/20 text-blue-300' :
                                    'bg-gray-500/20 text-gray-300'
                                  }`}>
                                    {asset.overall}
                                  </div>
                                  <span className="text-white">{asset.name}</span>
                                  <span className="text-[#94a3b8]">{asset.position}</span>
                                </>
                              ) : (
                                <span className="text-white">{asset.name}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-[#94a3b8] mb-1">You Receive:</div>
                        <div className="space-y-1">
                          {counter.receivingAssets.map(asset => (
                            <div key={asset.id} className="flex items-center gap-2 bg-[#1a2332] p-1.5 rounded text-xs">
                              {asset.type === 'player' ? (
                                <>
                                  <div className={`px-1.5 py-0.5 rounded text-xs ${
                                    asset.overall! >= 90 ? 'bg-green-500/20 text-green-300' :
                                    asset.overall! >= 85 ? 'bg-blue-500/20 text-blue-300' :
                                    'bg-gray-500/20 text-gray-300'
                                  }`}>
                                    {asset.overall}
                                  </div>
                                  <span className="text-white">{asset.name}</span>
                                  <span className="text-[#94a3b8]">{asset.position}</span>
                                </>
                              ) : (
                                <span className="text-white">{asset.name}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => handleAcceptCounter(counter, index)}
                      className="flex-1 bg-green-600 hover:bg-green-700 text-white text-xs h-8"
                    >
                      Accept Counter
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleRejectCounter(index)}
                      className="flex-1 bg-transparent border-red-500 text-red-400 hover:bg-red-500/10 text-xs h-8"
                    >
                      Reject
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
