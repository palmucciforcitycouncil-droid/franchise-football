import { useState, useEffect } from 'react';
import { HelpCircle } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/tabs';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { Badge } from '../ui/badge';
import { getCapSummary, CapSummaryResponse } from '../../lib/mockSalaryCapApi';
import { Skeleton } from '../ui/skeleton';

function formatCurrency(value: number): string {
  const millions = value / 1000000;
  return `$${millions.toFixed(1)}M`;
}

export function SalaryCapBox() {
  const [capData, setCapData] = useState<CapSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeYear, setActiveYear] = useState<string>('');

  useEffect(() => {
    loadCapData();
  }, []);

  const loadCapData = async () => {
    try {
      setLoading(true);
      const data = await getCapSummary();
      setCapData(data);
      // Set first year as default
      if (data.items.length > 0) {
        setActiveYear(data.items[0].year.toString());
      }
    } catch (error) {
      console.error('Failed to load cap data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] p-4 mb-6">
        <Skeleton className="h-6 w-32 mb-4 bg-[#1F2A35]" />
        <Skeleton className="h-10 w-full mb-4 bg-[#1F2A35]" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-24 bg-[#1F2A35]" />
          <Skeleton className="h-24 bg-[#1F2A35]" />
          <Skeleton className="h-24 bg-[#1F2A35]" />
        </div>
      </div>
    );
  }

  if (!capData || capData.items.length === 0) {
    return null;
  }

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] overflow-hidden mb-6">
      {/* Header */}
      <div className="bg-[#0a1929] p-4 border-b border-[#2d4a6f] flex items-center justify-between">
        <h3 className="text-white">Salary Cap</h3>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <button className="text-[#94a3b8] hover:text-white transition-colors">
                <HelpCircle className="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent 
              side="bottom" 
              className="bg-[#1a2332] border-[#2d4a6f] text-white max-w-xs"
            >
              <p className="text-sm">
                Future league caps are projections: we use the game's yearly cap growth formula 
                and round down to the nearest number ending in 0 or 5.
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Tabs */}
      <Tabs value={activeYear} onValueChange={setActiveYear}>
        <div className="px-4 pt-3 pb-0">
          <TabsList className="w-full bg-[#0a1929] p-1 grid grid-cols-4">
            {capData.items.map((item) => (
              <TabsTrigger
                key={item.year}
                value={item.year.toString()}
                className="data-[state=active]:bg-[#2d4a6f] data-[state=active]:text-white text-[#94a3b8]"
              >
                {item.year}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        {/* Content Area */}
        {capData.items.map((item) => (
          <TabsContent
            key={item.year}
            value={item.year.toString()}
            className="mt-0 p-4"
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Team Obligations */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <div className="text-xs text-[#94a3b8] mb-2">Team Obligations</div>
                <div className="text-2xl text-white">
                  {formatCurrency(item.team_obligations)}
                </div>
              </div>

              {/* League Cap */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <div className="flex items-center gap-2 mb-2">
                  <div className="text-xs text-[#94a3b8]">League Cap</div>
                  {item.is_projected && (
                    <Badge 
                      variant="outline" 
                      className="text-xs px-1.5 py-0 h-4 bg-[#2d4a6f]/50 border-[#2d4a6f] text-[#94a3b8]"
                    >
                      Projected
                    </Badge>
                  )}
                </div>
                <div className="text-2xl text-white">
                  {formatCurrency(item.league_cap)}
                </div>
              </div>

              {/* Cap Space */}
              <div className="bg-[#0a1929] p-4 rounded border border-[#2d4a6f]">
                <div className="text-xs text-[#94a3b8] mb-2">Cap Space</div>
                <div
                  className={`text-2xl ${
                    item.cap_space >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {item.cap_space >= 0 ? '+' : ''}
                  {formatCurrency(item.cap_space)}
                </div>
              </div>
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
