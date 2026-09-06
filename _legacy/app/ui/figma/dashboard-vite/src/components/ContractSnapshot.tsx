// Contract Snapshot per GDD v3.2 §9.2.2.1 Layout C3

import React from 'react';
import { ContractSummary } from '../types/roster';
import { DollarSign, Calendar, TrendingUp } from 'lucide-react';

interface ContractSnapshotProps {
  contractSummary: ContractSummary;
}

export function ContractSnapshot({ contractSummary }: ContractSnapshotProps) {
  const formatCurrency = (amount: number) => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `$${(amount / 1000).toFixed(0)}K`;
    }
    return `$${amount}`;
  };

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f]">
        <h3 className="text-white">Contract Snapshot</h3>
      </div>

      <div className="p-4 space-y-6">
        {/* Cap Space */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-[#d4af37]" />
            <h4 className="text-white text-sm font-medium">Cap Space</h4>
          </div>
          <div className="bg-[#0a1929] rounded-lg p-3">
            <div className="text-2xl font-bold text-[#d4af37]">
              {formatCurrency(contractSummary.cap_space)}
            </div>
            <div className="text-[#94a3b8] text-xs mt-1">
              Available for signings
            </div>
          </div>
        </div>

        {/* Top 5 Contracts */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-[#d4af37]" />
            <h4 className="text-white text-sm font-medium">Top 5 AAV</h4>
          </div>
          <div className="space-y-2">
            {contractSummary.top_contracts.map((contract, index) => (
              <div
                key={contract.player_id}
                className="flex items-center justify-between p-2 bg-[#0a1929] rounded border border-[#2d4a6f]"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[#d4af37] text-xs font-bold w-4">
                    {index + 1}
                  </span>
                  <div>
                    <div className="text-white text-sm">{contract.name}</div>
                    <div className="text-[#94a3b8] text-xs">{contract.pos}</div>
                  </div>
                </div>
                <div className="text-[#d4af37] text-sm font-medium">
                  {formatCurrency(contract.aav)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Expiring Contracts */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-[#d4af37]" />
            <h4 className="text-white text-sm font-medium">Expiring Soon</h4>
          </div>
          <div className="space-y-2">
            {contractSummary.expiring.slice(0, 5).map((contract) => (
              <div
                key={contract.player_id}
                className="flex items-center justify-between p-2 bg-[#0a1929] rounded border border-[#2d4a6f]"
              >
                <div>
                  <div className="text-white text-sm">{contract.name}</div>
                  <div className="text-[#94a3b8] text-xs">{contract.pos}</div>
                </div>
                <div className="text-right">
                  <div className="text-[#d4af37] text-sm font-medium">
                    {formatCurrency(contract.aav)}
                  </div>
                  <div className="text-[#94a3b8] text-xs">
                    Expires {contract.exp_year}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
