import { useState, useEffect } from 'react';
import { Users, TrendingUp, Search } from 'lucide-react';
import { RosterTable } from './RosterTable';
import { SalaryCapBox } from './gm/SalaryCapBox';
import { ExpiringContractsBox } from './gm/ExpiringContractsBox';
import { TopProspectsBox } from './gm/TopProspectsBox';
import { TradeBox } from './gm/TradeBox';
import { TradeBlockOfferBox } from './gm/TradeBlockOfferBox';
import { AvailablePlayersBox } from './gm/AvailablePlayersBox';
import { FindPlayerBox } from './gm/FindPlayerBox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { ExpiringContract } from '../lib/mockGMApi';
import { toast } from 'sonner@2.0.3';
import { Skeleton } from './ui/skeleton';

// Mock roster data
const DEMO_ROSTER = [
  { name: "J. Kingsley", num: 12, pos: "QB", age: 28, ovr: 84, spd: 78, str: 62, agi: 82, tpw: 91, tac: 86, cth: 48, tck: 22, awr: 85, pot: 88, sta: 92, inj: 18, mor: 74, ctr: "$8.5M", yrs: 2, dep: "QB1", hlth: "Q", trd: false },
  { name: "T. Morrow", num: 22, pos: "RB", age: 26, ovr: 82, spd: 90, str: 74, agi: 88, tpw: 40, tac: 42, cth: 76, tck: 35, awr: 78, pot: 85, sta: 88, inj: 12, mor: 79, ctr: "$4.2M", yrs: 3, dep: "RB1", hlth: "Healthy", trd: false },
  { name: "K. Benton", num: 11, pos: "WR", age: 27, ovr: 87, spd: 93, str: 68, agi: 91, tpw: 36, tac: 44, cth: 90, tck: 28, awr: 83, pot: 90, sta: 90, inj: 22, mor: 81, ctr: "$12.0M", yrs: 4, dep: "WR1", hlth: "Healthy", trd: true },
  { name: "M. Sanders", num: 7, pos: "QB", age: 24, ovr: 71, spd: 81, str: 58, agi: 79, tpw: 84, tac: 78, cth: 42, tck: 18, awr: 72, pot: 82, sta: 88, inj: 15, mor: 76, ctr: "$1.8M", yrs: 1, dep: "QB2", hlth: "Healthy", trd: false },
  { name: "D. Wright", num: 33, pos: "RB", age: 23, ovr: 76, spd: 88, str: 69, agi: 84, tpw: 38, tac: 40, cth: 72, tck: 32, awr: 74, pot: 83, sta: 85, inj: 20, mor: 82, ctr: "$2.1M", yrs: 2, dep: "RB2", hlth: "Healthy", trd: false },
  { name: "R. Hayes", num: 28, pos: "RB", age: 29, ovr: 79, spd: 86, str: 72, agi: 82, tpw: 35, tac: 38, cth: 74, tck: 30, awr: 80, pot: 79, sta: 82, inj: 25, mor: 68, ctr: "$3.5M", yrs: 1, dep: "RB3", hlth: "D", trd: false },
  { name: "L. Carter", num: 13, pos: "WR", age: 25, ovr: 83, spd: 91, str: 65, agi: 88, tpw: 34, tac: 42, cth: 88, tck: 26, awr: 81, pot: 87, sta: 87, inj: 18, mor: 85, ctr: "$6.8M", yrs: 3, dep: "WR2", hlth: "Healthy", trd: false },
  { name: "J. Thomas", num: 18, pos: "WR", age: 22, ovr: 74, spd: 92, str: 61, agi: 90, tpw: 32, tac: 40, cth: 82, tck: 24, awr: 73, pot: 85, sta: 90, inj: 12, mor: 88, ctr: "$1.2M", yrs: 2, dep: "WR3", hlth: "Healthy", trd: false },
  { name: "C. Matthews", num: 87, pos: "TE", age: 27, ovr: 85, spd: 82, str: 78, agi: 80, tpw: 38, tac: 45, cth: 86, tck: 48, awr: 82, pot: 86, sta: 88, inj: 20, mor: 80, ctr: "$7.5M", yrs: 3, dep: "TE1", hlth: "Healthy", trd: false },
  { name: "L. Jackson", num: 54, pos: "LB", age: 25, ovr: 85, spd: 82, str: 80, agi: 84, tpw: 35, tac: 40, cth: 62, tck: 82, awr: 85, pot: 88, sta: 90, inj: 18, mor: 86, ctr: "$9.5M", yrs: 4, dep: "MLB1", hlth: "Healthy", trd: false },
];

export function GMDeskPage() {
  const [rosterPlayers, setRosterPlayers] = useState(DEMO_ROSTER);
  const [rosterLoading, setRosterLoading] = useState(true);
  const [signingModalOpen, setSigningModalOpen] = useState(false);
  const [selectedContract, setSelectedContract] = useState<ExpiringContract | null>(null);
  const [offerYears, setOfferYears] = useState('');
  const [offerTotal, setOfferTotal] = useState('');
  const [positionFilter, setPositionFilter] = useState<string | null>(null);

  useEffect(() => {
    // Simulate loading roster
    const timer = setTimeout(() => {
      setRosterLoading(false);
    }, 800);
    return () => clearTimeout(timer);
  }, []);

  const handleContractClick = (contract: ExpiringContract) => {
    setSelectedContract(contract);
    setOfferYears(contract.desiredLength.toString());
    setOfferTotal(contract.desiredTotal.replace('$', '').replace('M', ''));
    setSigningModalOpen(true);
  };

  const handleSubmitOffer = () => {
    if (!selectedContract) return;
    
    const offerAPY = parseFloat(offerTotal) / parseInt(offerYears);
    const desiredAPY = parseFloat(selectedContract.desiredAPY.replace('$', '').replace('M', ''));
    
    // Simple acceptance logic
    if (offerAPY >= desiredAPY) {
      toast.success(`${selectedContract.name} has accepted your offer!`);
    } else if (offerAPY >= desiredAPY * 0.85) {
      toast.warning(`${selectedContract.name} is considering your offer. Negotiations ongoing...`);
    } else {
      toast.error(`${selectedContract.name} has rejected your offer. It's too low.`);
    }
    
    setSigningModalOpen(false);
    setSelectedContract(null);
  };

  // Calculate position quotas from actual roster
  const positionQuotas = {
    QB: { current: rosterPlayers.filter(p => p.pos === 'QB').length, min: 2 },
    RB: { current: rosterPlayers.filter(p => p.pos === 'RB').length, min: 3 },
    WR: { current: rosterPlayers.filter(p => p.pos === 'WR').length, min: 5 },
    TE: { current: rosterPlayers.filter(p => p.pos === 'TE').length, min: 2 },
    C: { current: rosterPlayers.filter(p => p.pos === 'C').length, min: 1 },
    G: { current: rosterPlayers.filter(p => p.pos === 'G').length, min: 2 },
    T: { current: rosterPlayers.filter(p => p.pos === 'T').length, min: 2 },
    DE: { current: rosterPlayers.filter(p => p.pos === 'DE').length, min: 2 },
    DT: { current: rosterPlayers.filter(p => p.pos === 'DT').length, min: 1 },
    LB: { current: rosterPlayers.filter(p => p.pos === 'LB').length, min: 6 },
    CB: { current: rosterPlayers.filter(p => p.pos === 'CB').length, min: 4 },
    S: { current: rosterPlayers.filter(p => p.pos === 'S').length, min: 4 },
    K: { current: rosterPlayers.filter(p => p.pos === 'K').length, min: 1 },
    P: { current: rosterPlayers.filter(p => p.pos === 'P').length, min: 1 },
    KR: { current: rosterPlayers.filter(p => p.pos === 'KR').length, min: 1 },
    PR: { current: rosterPlayers.filter(p => p.pos === 'PR').length, min: 1 },
  };

  return (
    <div className="max-w-[1920px] mx-auto">
      {/* Salary Cap Module - Top of Page */}
      <SalaryCapBox />

      {/* 3 Column Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Row 1 - Column 1: On The Block */}
        <div>
          <AvailablePlayersBox />
        </div>

        {/* Row 1 - Column 2: Top Prospects */}
        <div>
          <TopProspectsBox />
        </div>

        {/* Row 1 - Column 3: Expiring Contracts */}
        <div>
          <ExpiringContractsBox />
        </div>

        {/* Row 2 - Column 1: Trade Box */}
        <div>
          <TradeBox />
        </div>

        {/* Row 2 - Column 2: Find Player */}
        <div>
          <FindPlayerBox />
        </div>

        {/* Row 2 - Column 3: Trade Block Offer */}
        <div>
          <TradeBlockOfferBox />
        </div>
      </div>

      {/* Current Roster Section */}
      {rosterLoading ? (
        <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] p-6 space-y-3">
          {[...Array(10)].map((_, i) => (
            <Skeleton key={i} className="h-12 bg-[#1F2A35]" />
          ))}
        </div>
      ) : (
        <RosterTable
          players={rosterPlayers}
          stats={[]}
          viewMode="attributes"
          loading={false}
          error={false}
          searchQuery=""
          positionFilter={positionFilter}
          onPlayerClick={() => {}}
          positionQuotas={positionQuotas}
          onPositionFilterChange={setPositionFilter}
        />
      )}

      {/* Contract Signing Modal */}
      <Dialog open={signingModalOpen} onOpenChange={setSigningModalOpen}>
        <DialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white">Contract Offer</DialogTitle>
            <DialogDescription className="text-[#94a3b8]">
              Make a contract offer to {selectedContract?.name}
            </DialogDescription>
          </DialogHeader>

          {selectedContract && (
            <div className="space-y-4 py-4">
              {/* Player Info */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div className="text-white">{selectedContract.name}</div>
                    <div className="text-sm text-[#94a3b8]">
                      {selectedContract.position} · Age {selectedContract.age}
                    </div>
                  </div>
                  <div className={`px-2 py-1 rounded text-sm ${
                    selectedContract.overall >= 85 ? 'bg-green-500/20 text-green-300' :
                    'bg-blue-500/20 text-blue-300'
                  }`}>
                    OVR {selectedContract.overall}
                  </div>
                </div>
                <div className="pt-2 border-t border-[#2d4a6f] text-sm">
                  <div className="flex justify-between mb-1">
                    <span className="text-[#94a3b8]">Current Cap Hit:</span>
                    <span className="text-white">{selectedContract.currentCapHit}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#94a3b8]">Desired Contract:</span>
                    <span className="text-[#d4af37]">
                      {selectedContract.desiredLength}yr / {selectedContract.desiredTotal} ({selectedContract.desiredAPY}/yr)
                    </span>
                  </div>
                </div>
              </div>

              {/* Offer Form */}
              <div className="space-y-3">
                <div>
                  <Label htmlFor="years" className="text-white">Contract Length (years)</Label>
                  <Input
                    id="years"
                    type="number"
                    value={offerYears}
                    onChange={(e) => setOfferYears(e.target.value)}
                    className="bg-[#0a1929] border-[#2d4a6f] text-white mt-1"
                    min="1"
                    max="7"
                  />
                </div>
                <div>
                  <Label htmlFor="total" className="text-white">Total Value ($M)</Label>
                  <Input
                    id="total"
                    type="number"
                    value={offerTotal}
                    onChange={(e) => setOfferTotal(e.target.value)}
                    className="bg-[#0a1929] border-[#2d4a6f] text-white mt-1"
                    step="0.5"
                  />
                </div>
                {offerYears && offerTotal && (
                  <div className="bg-[#2d4a6f]/30 p-3 rounded">
                    <div className="text-sm text-[#94a3b8]">Average Per Year</div>
                    <div className="text-xl text-white">
                      ${(parseFloat(offerTotal) / parseInt(offerYears)).toFixed(1)}M
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  onClick={() => setSigningModalOpen(false)}
                  className="flex-1 bg-transparent border-[#2d4a6f] text-white hover:bg-[#2d4a6f]"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSubmitOffer}
                  disabled={!offerYears || !offerTotal}
                  className="flex-1 bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]"
                >
                  Submit Offer
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
