import { useState } from 'react';
import { Dialog, DialogContent } from '../ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Button } from '../ui/button';
import { X, HandshakeIcon, UserX } from 'lucide-react';
import { useGlobalModal } from '../../lib/GlobalModalContext';
import { ContractNegotiationModal } from './ContractNegotiationModal';
import { toast } from 'sonner@2.0.3';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../ui/alert-dialog';

export function PlayerCardModal() {
  const { selectedPlayer, isPlayerModalOpen, closePlayerModal } = useGlobalModal();
  const [activeTab, setActiveTab] = useState('overview');
  const [isNegotiationOpen, setIsNegotiationOpen] = useState(false);
  const [isReleaseDialogOpen, setIsReleaseDialogOpen] = useState(false);

  if (!selectedPlayer) return null;

  // Mock: Assume player is on user's team if they have depth chart position
  const isOnUserTeam = selectedPlayer.dep && selectedPlayer.dep !== 'FA';

  // Helper to get attribute rating with fallback
  const getAttr = (attr: string, fallback: number = 50) => {
    return selectedPlayer[attr.toLowerCase()] ?? fallback;
  };

  const getAttributeColor = (value: number) => {
    if (value >= 90) return 'text-[#d4af37]';
    if (value >= 80) return 'text-green-400';
    if (value >= 70) return 'text-blue-400';
    if (value >= 60) return 'text-white';
    return 'text-[#94a3b8]';
  };

  const handleNegotiate = () => {
    setIsNegotiationOpen(true);
  };

  const handleRelease = () => {
    setIsReleaseDialogOpen(true);
  };

  const confirmRelease = () => {
    toast.success(`${selectedPlayer.name} has been released from the team`);
    setIsReleaseDialogOpen(false);
    closePlayerModal();
  };

  return (
    <Dialog open={isPlayerModalOpen} onOpenChange={closePlayerModal}>
      <DialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-2xl p-0 gap-0" aria-describedby={undefined}>
        {/* Header Section */}
        <div className="p-6 pb-3 border-b border-[#2d4a6f]">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h2 className="text-white text-xl mb-1">{selectedPlayer.name}</h2>
              <div className="flex items-center gap-3 text-sm">
                <span className="text-[#d4af37]">#{selectedPlayer.num ?? '--'}</span>
                <span className="text-[#94a3b8]">{selectedPlayer.pos}</span>
                <span className="text-[#94a3b8]">Age {selectedPlayer.age}</span>
                <span className={`${getAttributeColor(selectedPlayer.ovr)}`}>
                  OVR {selectedPlayer.ovr}
                </span>
              </div>
            </div>
            <button
              onClick={closePlayerModal}
              className="text-[#94a3b8] hover:text-white transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="w-full bg-[#0a1929] p-1 h-auto">
              <TabsTrigger value="overview" className="flex-1 data-[state=active]:bg-[#2d4a6f]">
                Overview
              </TabsTrigger>
              <TabsTrigger value="ratings" className="flex-1 data-[state=active]:bg-[#2d4a6f]">
                Ratings
              </TabsTrigger>
              <TabsTrigger value="contract" className="flex-1 data-[state=active]:bg-[#2d4a6f]">
                Contract
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Scrollable Content */}
        <div className="overflow-y-auto max-h-[60vh] p-6">
          <Tabs value={activeTab}>
            {/* Overview Tab */}
            <TabsContent value="overview" className="mt-0 space-y-4">
              {/* Key Stats */}
              <div className="grid grid-cols-4 gap-3">
                {['SPD', 'STR', 'AGI', 'AWR'].map((attr) => {
                  const value = getAttr(attr);
                  return (
                    <div key={attr} className="bg-[#0a1929] p-3 rounded border border-[#2d4a6f] text-center">
                      <div className="text-[#94a3b8] text-xs mb-1">{attr}</div>
                      <div className={`text-xl ${getAttributeColor(value)}`}>{value}</div>
                    </div>
                  );
                })}
              </div>

              {/* Status */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <h4 className="text-white mb-3 text-sm">Status</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {selectedPlayer.hlth && (
                    <div className="flex justify-between">
                      <span className="text-[#94a3b8]">Health</span>
                      <span className="text-white">{selectedPlayer.hlth}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-[#94a3b8]">Morale</span>
                    <span className={getAttributeColor(getAttr('MOR'))}>{getAttr('MOR')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#94a3b8]">Injury</span>
                    <span className={getAttributeColor(getAttr('INJ'))}>{getAttr('INJ')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#94a3b8]">Stamina</span>
                    <span className={getAttributeColor(getAttr('STA'))}>{getAttr('STA')}</span>
                  </div>
                </div>
              </div>

              {/* Career Stats (Mock) */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <h4 className="text-white mb-3 text-sm">Career Stats</h4>
                <div className="grid grid-cols-3 gap-3 text-center text-sm">
                  <div>
                    <div className="text-2xl text-[#d4af37] mb-1">
                      {Math.floor(Math.random() * 100) + 50}
                    </div>
                    <div className="text-[#94a3b8] text-xs">Games</div>
                  </div>
                  <div>
                    <div className="text-2xl text-[#d4af37] mb-1">
                      {Math.floor(Math.random() * 50) + 10}
                    </div>
                    <div className="text-[#94a3b8] text-xs">Starts</div>
                  </div>
                  <div>
                    <div className="text-2xl text-[#d4af37] mb-1">
                      {Math.floor(Math.random() * 3) + 1}
                    </div>
                    <div className="text-[#94a3b8] text-xs">Pro Bowls</div>
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* Ratings Tab */}
            <TabsContent value="ratings" className="mt-0 space-y-4">
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <h4 className="text-white mb-3 text-sm">All Attributes</h4>
                <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
                  {['SPD', 'STR', 'AGI', 'TPW', 'TAC', 'CTH', 'TCK', 'AWR', 'POT', 'STA', 'INJ', 'MOR'].map((attr) => {
                    const value = getAttr(attr);
                    return (
                      <div key={attr} className="flex items-center justify-between py-1">
                        <span className="text-[#94a3b8]">{attr}</span>
                        <span className={getAttributeColor(value)}>{value}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </TabsContent>

            {/* Contract Tab */}
            <TabsContent value="contract" className="mt-0 space-y-4">
              {selectedPlayer.ctr ? (
                <>
                  <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                    <h4 className="text-white mb-3 text-sm">Contract Details</h4>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between py-2 border-b border-[#2d4a6f]">
                        <span className="text-[#94a3b8]">Salary</span>
                        <span className="text-white">{selectedPlayer.ctr}</span>
                      </div>
                      {selectedPlayer.yrs !== undefined && (
                        <div className="flex justify-between py-2 border-b border-[#2d4a6f]">
                          <span className="text-[#94a3b8]">Years Remaining</span>
                          <span className="text-white">{selectedPlayer.yrs}</span>
                        </div>
                      )}
                      {selectedPlayer.dep && (
                        <div className="flex justify-between py-2 border-b border-[#2d4a6f]">
                          <span className="text-[#94a3b8]">Depth Chart</span>
                          <span className="text-white">{selectedPlayer.dep}</span>
                        </div>
                      )}
                      {selectedPlayer.trd !== undefined && (
                        <div className="flex justify-between py-2">
                          <span className="text-[#94a3b8]">Trade Block</span>
                          <span className={selectedPlayer.trd ? 'text-[#d4af37]' : 'text-white'}>
                            {selectedPlayer.trd ? 'Yes' : 'No'}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-3">
                    <Button
                      onClick={handleNegotiate}
                      className="flex-1 bg-transparent border border-[#d4af37] text-[#d4af37] hover:bg-[#d4af37]/10"
                    >
                      <HandshakeIcon className="h-4 w-4 mr-2" />
                      Negotiate
                    </Button>
                    {isOnUserTeam && (
                      <Button
                        onClick={handleRelease}
                        variant="outline"
                        className="flex-1 bg-transparent border-red-500/50 text-red-400 hover:bg-red-500/10 hover:text-red-300"
                      >
                        <UserX className="h-4 w-4 mr-2" />
                        Release
                      </Button>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <div className="bg-[#0a1929] p-8 rounded border border-[#2d4a6f] text-center">
                    <p className="text-[#94a3b8]">No contract information available</p>
                  </div>
                  
                  {/* Show negotiate button for free agents */}
                  <Button
                    onClick={handleNegotiate}
                    className="w-full bg-transparent border border-[#d4af37] text-[#d4af37] hover:bg-[#d4af37]/10"
                  >
                    <HandshakeIcon className="h-4 w-4 mr-2" />
                    Negotiate Contract
                  </Button>
                </>
              )}
            </TabsContent>
          </Tabs>
        </div>

        {/* Contract Negotiation Modal */}
        <ContractNegotiationModal
          isOpen={isNegotiationOpen}
          onClose={() => setIsNegotiationOpen(false)}
          playerName={selectedPlayer.name}
          playerPosition={selectedPlayer.pos}
          playerOvr={selectedPlayer.ovr}
          currentSalary={selectedPlayer.ctr}
          currentYears={selectedPlayer.yrs}
        />

        {/* Release Confirmation Dialog */}
        <AlertDialog open={isReleaseDialogOpen} onOpenChange={setIsReleaseDialogOpen}>
          <AlertDialogContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
            <AlertDialogHeader>
              <AlertDialogTitle>Release {selectedPlayer.name}?</AlertDialogTitle>
              <AlertDialogDescription className="text-[#94a3b8]">
                Are you sure you want to release this player? This action cannot be undone.
                {selectedPlayer.ctr && (
                  <span className="block mt-2">
                    Remaining contract: {selectedPlayer.ctr} for {selectedPlayer.yrs || 0} year(s)
                  </span>
                )}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="bg-transparent border-[#2d4a6f] text-[#94a3b8] hover:bg-[#2d4a6f]/30 hover:text-white">
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
      </DialogContent>
    </Dialog>
  );
}
