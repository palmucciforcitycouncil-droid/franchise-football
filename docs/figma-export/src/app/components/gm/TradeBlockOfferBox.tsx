import { useState, useEffect } from 'react';
import { Send, X, TrendingUp, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { 
  TradeAsset,
  TradeOffer,
  TradePreference,
  getYourRoster,
  getYourPicks,
  submitTradeOffer
} from '../../lib/mockTradeBlockApi';
import { toast } from 'sonner@2.0.3';

export function TradeBlockOfferBox() {
  const [yourRoster, setYourRoster] = useState<TradeAsset[]>([]);
  const [yourPicks, setYourPicks] = useState<TradeAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAssets, setSelectedAssets] = useState<TradeAsset[]>([]);
  const [tradePreference, setTradePreference] = useState<TradePreference>('any');
  const [specificPosition, setSpecificPosition] = useState<string>('');
  const [showingOffer, setShowingOffer] = useState(false);
  const [allOffers, setAllOffers] = useState<TradeOffer[]>([]);
  const [currentOfferIndex, setCurrentOfferIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  const rosterPositions = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'CB', 'S'];

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [roster, picks] = await Promise.all([
        getYourRoster(),
        getYourPicks(),
      ]);
      setYourRoster(roster);
      setYourPicks(picks);
    } catch (error) {
      console.error('Failed to load trade assets:', error);
      toast.error('Failed to load trade assets');
    } finally {
      setLoading(false);
    }
  };

  const toggleAssetSelection = (asset: TradeAsset) => {
    setSelectedAssets(current => {
      const exists = current.find(a => a.id === asset.id);
      if (exists) {
        return current.filter(a => a.id !== asset.id);
      }
      return [...current, asset];
    });
  };

  const handleSubmitOffer = async () => {
    if (selectedAssets.length === 0) {
      toast.error('Please select at least one asset to trade');
      return;
    }

    try {
      setSubmitting(true);
      const offers = await submitTradeOffer(
        selectedAssets,
        tradePreference,
        specificPosition
      );
      setAllOffers(offers);
      setCurrentOfferIndex(0);
      setShowingOffer(true);
      toast.success(`${offers.length} trade offer${offers.length > 1 ? 's' : ''} received!`);
    } catch (error) {
      console.error('Failed to submit trade offer:', error);
      toast.error('Failed to submit trade offer');
    } finally {
      setSubmitting(false);
    }
  };

  const handleClearOffer = () => {
    setSelectedAssets([]);
    setTradePreference('any');
    setSpecificPosition('');
    setAllOffers([]);
    setCurrentOfferIndex(0);
    setShowingOffer(false);
  };

  const handlePreviousOffer = () => {
    setCurrentOfferIndex(prev => Math.max(0, prev - 1));
  };

  const handleNextOffer = () => {
    setCurrentOfferIndex(prev => Math.min(allOffers.length - 1, prev + 1));
  };

  const getInterestBadgeColor = (interest: string) => {
    switch (interest) {
      case 'high': return 'bg-[#4ade80]/10 text-[#4ade80] border-[#4ade80]/30';
      case 'medium': return 'bg-[#fbbf24]/10 text-[#fbbf24] border-[#fbbf24]/30';
      case 'low': return 'bg-[#94a3b8]/10 text-[#94a3b8] border-[#94a3b8]/30';
      default: return 'bg-[#94a3b8]/10 text-[#94a3b8] border-[#94a3b8]/30';
    }
  };

  if (loading) {
    return (
      <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] p-6">
        <div className="text-center py-8 text-[#94a3b8]">Loading...</div>
      </div>
    );
  }

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] flex flex-col h-[700px]">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f] flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Send className="h-5 w-5 text-[#d4af37]" />
            <h3 className="text-white">Trade Block Offers</h3>
          </div>
          {selectedAssets.length > 0 && (
            <Button
              size="sm"
              variant="ghost"
              onClick={handleClearOffer}
              className="text-[#94a3b8] hover:text-white h-8"
            >
              <X className="h-4 w-4 mr-1" />
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-2.5 flex-1 overflow-y-auto">
          {/* Selected Assets Display */}
          {selectedAssets.length > 0 && (
            <div className="bg-[#0a1929] rounded p-2 border border-[#2d4a6f]">
              <div className="text-xs text-[#94a3b8] mb-1.5">Offering ({selectedAssets.length})</div>
              <div className="space-y-1.5">
                {selectedAssets.map(asset => (
                  <div
                    key={asset.id}
                    className="flex items-center justify-between bg-[#1a2332] p-1.5 rounded text-sm"
                  >
                    <div>
                      {asset.type === 'player' ? (
                        <>
                          <span className="text-white text-xs">{asset.name}</span>
                          <span className="text-[#94a3b8] ml-2 text-xs">
                            {asset.position} · {asset.overall}
                          </span>
                        </>
                      ) : (
                        <span className="text-white text-xs">
                          {asset.year} Rd {asset.round}
                          {asset.pickNumber && ` (#${asset.pickNumber})`}
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => toggleAssetSelection(asset)}
                      className="text-red-400 hover:text-red-300"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Trade Preferences */}
          <div className="space-y-1.5">
            <div className="text-xs text-[#94a3b8]">Looking for:</div>
            
            <Select value={tradePreference} onValueChange={(value: TradePreference) => setTradePreference(value)}>
              <SelectTrigger className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                <SelectItem value="any">Any Offers</SelectItem>
                <SelectItem value="position">Specific Position</SelectItem>
                <SelectItem value="prospect">Young Prospects</SelectItem>
                <SelectItem value="veteran">Veteran Players</SelectItem>
                <SelectItem value="picks">Draft Picks</SelectItem>
              </SelectContent>
            </Select>

            {tradePreference === 'position' && (
              <Select value={specificPosition} onValueChange={setSpecificPosition}>
                <SelectTrigger className="bg-[#0a1929] border-[#2d4a6f] text-white h-8 text-xs">
                  <SelectValue placeholder="Select position..." />
                </SelectTrigger>
                <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
                  {rosterPositions.map(pos => (
                    <SelectItem key={pos} value={pos}>{pos}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Submit Button */}
          <Button
            onClick={handleSubmitOffer}
            disabled={selectedAssets.length === 0 || submitting}
            className="w-full bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929] h-8 text-xs"
          >
            {submitting ? 'Generating Offers...' : 'Get Trade Offers'}
          </Button>

          {/* Asset Selection */}
          <div className="space-y-1.5">
            <div className="text-xs text-[#94a3b8]">Select Assets</div>
            <div className="max-h-[140px] overflow-y-auto space-y-1">
              {yourRoster.slice(0, 5).map(player => (
                <div
                  key={player.id}
                  onClick={() => toggleAssetSelection(player)}
                  className={`p-1.5 rounded cursor-pointer transition-colors ${
                    selectedAssets.find(a => a.id === player.id)
                      ? 'bg-[#d4af37]/20 border border-[#d4af37]'
                      : 'bg-[#0a1929] border border-[#2d4a6f] hover:border-[#d4af37]/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-white text-xs">{player.name}</div>
                      <div className="text-xs text-[#94a3b8]">
                        {player.position} · {player.overall}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {yourPicks.slice(0, 3).map(pick => (
                <div
                  key={pick.id}
                  onClick={() => toggleAssetSelection(pick)}
                  className={`p-1.5 rounded cursor-pointer transition-colors ${
                    selectedAssets.find(a => a.id === pick.id)
                      ? 'bg-[#d4af37]/20 border border-[#d4af37]'
                      : 'bg-[#0a1929] border border-[#2d4a6f] hover:border-[#d4af37]/50'
                  }`}
                >
                  <div className="text-white text-xs">
                    {pick.year} Rd {pick.round}
                    {pick.pickNumber && ` (#${pick.pickNumber})`}
                  </div>
                </div>
              ))}
            </div>
          </div>

        {/* Trade Response Area - Always visible */}
        <div className="mt-2.5 border border-[#2d4a6f] rounded-lg">
          {showingOffer && allOffers.length > 0 ? (
            <div className="border-[#d4af37]" style={{ borderColor: '#d4af37' }}>
            <div className="bg-gradient-to-r from-[#d4af37]/20 to-transparent p-2 border-b border-[#d4af37]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-3.5 w-3.5 text-[#d4af37]" />
                  <div className="flex items-center gap-2">
                    <h4 className="text-white text-xs">Offer Received</h4>
                    {allOffers.length > 1 && (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={handlePreviousOffer}
                          disabled={currentOfferIndex === 0}
                          className="p-0.5 hover:bg-[#d4af37]/20 rounded disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          <ChevronLeft className="h-3.5 w-3.5 text-[#d4af37]" />
                        </button>
                        <span className="text-[#94a3b8] text-xs">
                          ({currentOfferIndex + 1} of {allOffers.length})
                        </span>
                        <button
                          onClick={handleNextOffer}
                          disabled={currentOfferIndex === allOffers.length - 1}
                          className="p-0.5 hover:bg-[#d4af37]/20 rounded disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          <ChevronRight className="h-3.5 w-3.5 text-[#d4af37]" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                <div className={`px-1.5 py-0.5 rounded text-xs border ${getInterestBadgeColor(allOffers[currentOfferIndex].interest)}`}>
                  {allOffers[currentOfferIndex].interest.toUpperCase()}
                </div>
              </div>
              {allOffers[currentOfferIndex].fromTeam && (
                <div className="text-[#94a3b8] text-xs mt-1">
                  From: {allOffers[currentOfferIndex].fromTeam}
                </div>
              )}
            </div>

            <div className="p-2.5 space-y-2">
              {allOffers[currentOfferIndex].aiResponse && (
                <div className="text-xs text-[#94a3b8] italic">
                  "{allOffers[currentOfferIndex].aiResponse}"
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                {/* They Want */}
                <div>
                  <div className="text-xs text-[#94a3b8] mb-1">They Want:</div>
                  <div className="space-y-1">
                    {allOffers[currentOfferIndex].offeredAssets.map((asset, idx) => (
                      <div key={idx} className="bg-[#0a1929] p-1.5 rounded text-xs">
                        {asset.type === 'player' ? (
                          <div>
                            <div className="text-white">{asset.name}</div>
                            <div className="text-[#94a3b8] text-xs mt-0.5">
                              {asset.position} · {asset.overall} OVR
                            </div>
                            {asset.contract && (
                              <div className="text-[#94a3b8] text-xs">
                                {asset.contract}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="text-white">
                            {asset.year} Rd {asset.round}
                            {asset.pickNumber && ` (#${asset.pickNumber})`}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* They Offer */}
                <div>
                  <div className="text-xs text-[#94a3b8] mb-1">They Offer:</div>
                  <div className="space-y-1">
                    {allOffers[currentOfferIndex].requestedAssets.map((asset, idx) => (
                      <div key={idx} className="bg-[#0a1929] p-1.5 rounded text-xs border border-[#d4af37]/30">
                        {asset.type === 'player' ? (
                          <div>
                            <div className="text-white">{asset.name}</div>
                            <div className="text-[#94a3b8] text-xs mt-0.5">
                              {asset.position} · {asset.overall} OVR
                            </div>
                            {asset.contract && (
                              <div className="text-[#94a3b8] text-xs">
                                {asset.contract}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="text-white">
                            {asset.year} Rd {asset.round}
                            {asset.pickNumber && ` (#${asset.pickNumber})`}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  size="sm"
                  className="flex-1 bg-[#4ade80] hover:bg-[#3cc76a] text-[#0a1929] h-8 text-xs"
                  onClick={() => {
                    toast.success('Trade accepted! (Mock)');
                    handleClearOffer();
                  }}
                >
                  Accept
                </Button>
                <Button
                  size="sm"
                  className="flex-1 bg-transparent border border-[#2d4a6f] text-white hover:bg-[#2d4a6f] h-8 text-xs"
                  onClick={() => setShowingOffer(false)}
                >
                  Decline
                </Button>
              </div>
            </div>
            </div>
          ) : (
            /* Empty State */
            <div className="p-8 text-center">
              <div className="w-12 h-12 bg-[#d4af37]/10 rounded-full flex items-center justify-center mx-auto mb-3">
                <TrendingUp className="h-6 w-6 text-[#d4af37]" />
              </div>
              <h4 className="text-white text-sm mb-1">No Active Offers</h4>
              <p className="text-[#94a3b8] text-xs">
                Select assets and click "Get Trade Offers" to receive proposals from other teams
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
