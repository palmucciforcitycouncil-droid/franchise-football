// Injury Report per GDD v3.2 §9.2.2.1 Layout C3

import React from 'react';
import { InjuryRow } from '../types/roster';
import { AlertTriangle, Clock, Shield } from 'lucide-react';

interface InjuryReportProps {
  injuries: InjuryRow[];
}

export function InjuryReport({ injuries }: InjuryReportProps) {
  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'minor':
        return 'text-green-400';
      case 'moderate':
        return 'text-yellow-400';
      case 'major':
        return 'text-red-400';
      default:
        return 'text-[#94a3b8]';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'minor':
        return <Shield className="h-3 w-3 text-green-400" />;
      case 'moderate':
        return <AlertTriangle className="h-3 w-3 text-yellow-400" />;
      case 'major':
        return <AlertTriangle className="h-3 w-3 text-red-400" />;
      default:
        return <AlertTriangle className="h-3 w-3 text-[#94a3b8]" />;
    }
  };

  const getStatusText = (weeksRemaining: number) => {
    if (weeksRemaining === 0) {
      return 'Ready to return';
    } else if (weeksRemaining === 1) {
      return '1 week';
    } else {
      return `${weeksRemaining} weeks`;
    }
  };

  const getRTPPenaltyText = (penalty: number) => {
    if (penalty === 0) {
      return 'No penalty';
    } else if (penalty <= 0.1) {
      return 'Minimal penalty';
    } else if (penalty <= 0.2) {
      return 'Moderate penalty';
    } else {
      return 'Significant penalty';
    }
  };

  const getRTPPenaltyColor = (penalty: number) => {
    if (penalty === 0) {
      return 'text-green-400';
    } else if (penalty <= 0.1) {
      return 'text-yellow-400';
    } else if (penalty <= 0.2) {
      return 'text-orange-400';
    } else {
      return 'text-red-400';
    }
  };

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f]">
        <h3 className="text-white">Injury Report</h3>
      </div>

      <div className="p-4">
        {injuries.length === 0 ? (
          <div className="text-center py-8">
            <Shield className="h-8 w-8 text-green-400 mx-auto mb-2" />
            <div className="text-white text-sm">No Active Injuries</div>
            <div className="text-[#94a3b8] text-xs">All players healthy</div>
          </div>
        ) : (
          <div className="space-y-3">
            {injuries.map((injury) => (
              <div
                key={injury.player_id}
                className="p-3 bg-[#0a1929] rounded-lg border border-[#2d4a6f]"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {getSeverityIcon(injury.severity)}
                    <div>
                      <div className="text-white text-sm font-medium">
                        {injury.player_id}
                      </div>
                      <div className="text-[#94a3b8] text-xs">
                        {injury.type}
                      </div>
                    </div>
                  </div>
                  <div className={`text-xs font-medium ${getSeverityColor(injury.severity)}`}>
                    {injury.severity}
                  </div>
                </div>

                <div className="space-y-2">
                  {/* ETA */}
                  <div className="flex items-center gap-2">
                    <Clock className="h-3 w-3 text-[#94a3b8]" />
                    <span className="text-[#94a3b8] text-xs">
                      ETA: {getStatusText(injury.weeks_remaining)}
                    </span>
                  </div>

                  {/* RTP Penalty */}
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-3 w-3 text-[#94a3b8]" />
                    <span className={`text-xs ${getRTPPenaltyColor(injury.rtp_penalty)}`}>
                      RTP: {getRTPPenaltyText(injury.rtp_penalty)}
                      {injury.rtp_penalty > 0 && (
                        <span className="ml-1">
                          ({Math.round(injury.rtp_penalty * 100)}%)
                        </span>
                      )}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
