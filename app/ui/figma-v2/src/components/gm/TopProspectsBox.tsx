import { useState, useEffect } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Skeleton } from '../ui/skeleton';
import { TrendingUp } from 'lucide-react';
import { getTopProspects, TopProspect } from '../../lib/mockGMApi';
import { ClickablePlayerName } from '../ui/ClickablePlayerName';

export function TopProspectsBox() {
  const [selectedPosition, setSelectedPosition] = useState('QB');
  const [prospects, setProspects] = useState<TopProspect[]>([]);
  const [loading, setLoading] = useState(true);

  const positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'DB'];

  useEffect(() => {
    loadProspects();
  }, [selectedPosition]);

  const loadProspects = async () => {
    setLoading(true);
    try {
      const data = await getTopProspects(selectedPosition);
      setProspects(data);
    } catch (err) {
      console.error('Failed to load prospects:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f]">
      <div className="p-4 border-b border-[#2d4a6f]">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="h-5 w-5 text-[#d4af37]" />
          <h3 className="text-white">Top Prospects</h3>
        </div>
        <Select value={selectedPosition} onValueChange={setSelectedPosition}>
          <SelectTrigger className="w-full bg-[#0a1929] border-[#2d4a6f] text-white">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-[#1a2332] border-[#2d4a6f] text-white">
            {positions.map((pos) => (
              <SelectItem key={pos} value={pos} className="hover:bg-[#2d4a6f]">
                {pos}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="p-4">
        {loading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-16 bg-[#2d4a6f]" />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {prospects.map((prospect, index) => (
              <div
                key={index}
                className="bg-[#0a1929] p-3 rounded border border-[#2d4a6f] hover:border-[#d4af37] cursor-pointer transition-colors"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-[#2d4a6f] flex items-center justify-center text-xs text-white">
                      {index + 1}
                    </div>
                    <div>
                      <div className="text-white text-sm">
                        <ClickablePlayerName playerName={prospect.name} />
                      </div>
                      <div className="text-xs text-[#94a3b8]">
                        {prospect.school} · {prospect.position}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`px-2 py-0.5 rounded text-xs inline-block ${
                      prospect.potential >= 90 ? 'bg-green-500/20 text-green-300' :
                      prospect.potential >= 85 ? 'bg-blue-500/20 text-blue-300' :
                      'bg-gray-500/20 text-gray-300'
                    }`}>
                      POT {prospect.potential}
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[#94a3b8]">Age {prospect.age} · OVR {prospect.overall}</span>
                  <span className="text-[#d4af37]">Round {prospect.round}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
