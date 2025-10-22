// Player Card Panel per GDD v3.2 §9.2.2.1 Layout C2

import React, { useState } from 'react';
import { PlayerRow } from '../types/roster';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { BarChart3, Calendar, FileText } from 'lucide-react';

interface PlayerCardPanelProps {
  selectedPlayer: PlayerRow | null;
  onClose: () => void;
}

export function PlayerCardPanel({ selectedPlayer, onClose }: PlayerCardPanelProps) {
  const [activeTab, setActiveTab] = useState('attributes');

  if (!selectedPlayer) {
    return (
      <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] p-8">
        <div className="text-center text-[#94a3b8]">
          <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Select a player to view details</p>
        </div>
      </div>
    );
  }

  const formatCurrency = (amount: number) => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `$${(amount / 1000).toFixed(0)}K`;
    }
    return `$${amount}`;
  };

  const getHealthStatusColor = (status?: string) => {
    switch (status) {
      case 'Healthy':
        return 'bg-green-500/20 text-green-400';
      case 'Q':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'D':
        return 'bg-red-500/20 text-red-400';
      case 'OOS':
        return 'bg-red-500/20 text-red-400';
      default:
        return 'bg-green-500/20 text-green-400';
    }
  };

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f]">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-white text-lg font-medium">{selectedPlayer.name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[#94a3b8] text-sm">{selectedPlayer.pos}</span>
              <span className="text-[#d4af37] text-sm font-medium">
                OVR {selectedPlayer.ovr}
              </span>
              <Badge className={getHealthStatusColor(selectedPlayer.status.injury)}>
                {selectedPlayer.status.injury || 'Healthy'}
              </Badge>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#94a3b8] hover:text-white transition-colors"
          >
            ×
          </button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="p-4">
        <TabsList className="grid w-full grid-cols-3 bg-[#0a1929]">
          <TabsTrigger 
            value="attributes" 
            className="data-[state=active]:bg-[#d4af37] data-[state=active]:text-[#0a1929]"
          >
            <BarChart3 className="h-4 w-4 mr-2" />
            Attributes
          </TabsTrigger>
          <TabsTrigger 
            value="games" 
            className="data-[state=active]:bg-[#d4af37] data-[state=active]:text-[#0a1929]"
          >
            <Calendar className="h-4 w-4 mr-2" />
            Recent Games
          </TabsTrigger>
          <TabsTrigger 
            value="contract" 
            className="data-[state=active]:bg-[#d4af37] data-[state=active]:text-[#0a1929]"
          >
            <FileText className="h-4 w-4 mr-2" />
            Contract
          </TabsTrigger>
        </TabsList>

        {/* Attributes Tab */}
        <TabsContent value="attributes" className="mt-4">
          <div className="grid grid-cols-2 gap-4">
            <Card className="bg-[#0a1929] border-[#2d4a6f]">
              <CardHeader className="pb-2">
                <CardTitle className="text-white text-sm">Physical</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-[#94a3b8] text-xs">Age</span>
                  <span className="text-white text-xs">{selectedPlayer.age}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8] text-xs">Overall</span>
                  <span className="text-[#d4af37] text-xs font-medium">{selectedPlayer.ovr}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8] text-xs">Potential</span>
                  <span className="text-white text-xs">{selectedPlayer.pot}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-[#0a1929] border-[#2d4a6f]">
              <CardHeader className="pb-2">
                <CardTitle className="text-white text-sm">Contract Info</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-[#94a3b8] text-xs">AAV</span>
                  <span className="text-[#d4af37] text-xs font-medium">
                    {formatCurrency(selectedPlayer.contract.aav)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8] text-xs">Years</span>
                  <span className="text-white text-xs">{selectedPlayer.contract.years}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#94a3b8] text-xs">Expires</span>
                  <span className="text-white text-xs">{selectedPlayer.contract.exp}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Recent Games Tab */}
        <TabsContent value="games" className="mt-4">
          <Card className="bg-[#0a1929] border-[#2d4a6f]">
            <CardHeader className="pb-2">
              <CardTitle className="text-white text-sm">Recent Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-[#94a3b8]">
                <Calendar className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Game stats coming soon</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Contract Tab */}
        <TabsContent value="contract" className="mt-4">
          <Card className="bg-[#0a1929] border-[#2d4a6f]">
            <CardHeader className="pb-2">
              <CardTitle className="text-white text-sm">Contract Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-[#94a3b8] text-xs mb-1">Annual Average Value</div>
                  <div className="text-[#d4af37] text-lg font-bold">
                    {formatCurrency(selectedPlayer.contract.aav)}
                  </div>
                </div>
                <div>
                  <div className="text-[#94a3b8] text-xs mb-1">Contract Length</div>
                  <div className="text-white text-lg font-bold">
                    {selectedPlayer.contract.years} years
                  </div>
                </div>
              </div>
              
              <div>
                <div className="text-[#94a3b8] text-xs mb-1">Expiration</div>
                <div className="text-white text-sm">
                  {selectedPlayer.contract.exp}
                </div>
              </div>

              <div className="pt-2 border-t border-[#2d4a6f]">
                <div className="text-[#94a3b8] text-xs">
                  Contract details and negotiations will be available in future updates.
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
