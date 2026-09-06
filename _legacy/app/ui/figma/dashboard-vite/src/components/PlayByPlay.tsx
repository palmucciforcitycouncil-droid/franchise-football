import { useState, useEffect, useRef } from 'react';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { ScrollArea } from './ui/scroll-area';
import { Button } from './ui/button';

interface PlayEvent {
  quarter: number;
  time: string;
  down_distance: string;
  yardline: string;
  team_id: string;
  description: string;
  result: 'positive' | 'negative' | 'neutral';
}

const DEMO_DATA: PlayEvent[] = [
  { quarter: 4, time: "0:00", down_distance: "—", yardline: "—", team_id: "NE", description: "End of game. NE wins 27-17.", result: 'positive' },
  { quarter: 4, time: "0:42", down_distance: "1st & 10", yardline: "BUF 45", team_id: "NE", description: "R. Stevenson rush for 3 yards to BUF 42.", result: 'positive' },
  { quarter: 4, time: "1:15", down_distance: "2nd & 7", yardline: "NE 48", team_id: "NE", description: "M. Jones pass complete to D. Parker for 12 yards to BUF 40. 1st Down.", result: 'positive' },
  { quarter: 4, time: "1:52", down_distance: "1st & 10", yardline: "NE 48", team_id: "NE", description: "R. Stevenson rush for no gain.", result: 'neutral' },
  { quarter: 4, time: "2:31", down_distance: "3rd & 2", yardline: "NE 42", team_id: "BUF", description: "J. Allen pass incomplete intended for S. Diggs.", result: 'negative' },
  { quarter: 4, time: "2:36", down_distance: "2nd & 2", yardline: "NE 42", team_id: "BUF", description: "J. Cook rush for no gain. Tackled by M. Judon.", result: 'negative' },
  { quarter: 4, time: "3:18", down_distance: "1st & 10", yardline: "NE 42", team_id: "BUF", description: "J. Allen pass complete to G. Davis for 8 yards.", result: 'neutral' },
  { quarter: 4, time: "4:02", down_distance: "2nd & 15", yardline: "BUF 43", team_id: "BUF", description: "J. Allen sacked by M. Judon for -5 yards.", result: 'negative' },
  { quarter: 4, time: "4:28", down_distance: "1st & 10", yardline: "BUF 48", team_id: "BUF", description: "J. Allen pass complete to S. Diggs for 15 yards. 1st Down.", result: 'positive' },
  { quarter: 4, time: "5:11", down_distance: "4th & 3", yardline: "BUF 33", team_id: "BUF", description: "BUF punts 45 yards. Fair catch by M. Slater at NE 22.", result: 'neutral' },
  { quarter: 3, time: "14:42", down_distance: "1st & 10", yardline: "BUF 25", team_id: "NE", description: "M. Jones pass complete to H. Henry for TOUCHDOWN.", result: 'positive' },
  { quarter: 3, time: "15:00", down_distance: "Kickoff", yardline: "—", team_id: "BUF", description: "T. Bass kicks off 65 yards. Returned by M. Slater for 22 yards.", result: 'neutral' },
];

export function PlayByPlay() {
  const [data, setData] = useState<PlayEvent[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [activeQuarter, setActiveQuarter] = useState<number | null>(null);
  
  const q1Ref = useRef<HTMLDivElement>(null);
  const q2Ref = useRef<HTMLDivElement>(null);
  const q3Ref = useRef<HTMLDivElement>(null);
  const q4Ref = useRef<HTMLDivElement>(null);

  const scrollToQuarter = (quarter: number) => {
    setActiveQuarter(quarter);
    const refs = [q1Ref, q2Ref, q3Ref, q4Ref];
    const targetRef = refs[quarter - 1];
    
    if (targetRef.current) {
      targetRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      setData(DEMO_DATA);
      setLoading(false);
    }, 800);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] flex flex-col h-[520px]">
      {/* Header */}
      <div className="p-4 border-b border-[#2d4a6f] flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-white">Play-by-Play — Last Game</h3>
          <div className="flex gap-2">
            {[1, 2, 3, 4].map((quarter) => (
              <Button
                key={quarter}
                variant={activeQuarter === quarter ? "default" : "outline"}
                size="sm"
                onClick={() => scrollToQuarter(quarter)}
                className={`h-7 px-3 ${
                  activeQuarter === quarter
                    ? 'bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929]'
                    : 'bg-transparent border-[#2d4a6f] text-[#94a3b8] hover:bg-[#2d4a6f]/30 hover:text-white'
                }`}
              >
                {quarter}Q
              </Button>
            ))}
          </div>
        </div>
        <p className="text-[#94a3b8] text-xs">(demo)</p>
      </div>

      {error && (
        <div className="px-4 pt-3 flex-shrink-0">
          <Alert className="bg-[#991b1b]/20 border-[#dc2626] text-white">
            <AlertDescription className="text-sm">
              Couldn't load play-by-play. Showing demo.
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Content with Scroll */}
      <div className="flex-1 overflow-hidden">
        {loading ? (
          <div className="p-4 space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-16 w-full bg-[#2d4a6f]" />
            ))}
          </div>
        ) : (
          <ScrollArea className="h-full">
            <div className="p-4">
              {data && data.length > 0 ? (
                <div className="space-y-3">
                  {data.map((play, idx) => {
                    // Determine if this is the first play of a new quarter
                    const isFirstOfQuarter = idx === 0 || data[idx - 1]?.quarter !== play.quarter;
                    const quarterRef = 
                      play.quarter === 1 ? q1Ref :
                      play.quarter === 2 ? q2Ref :
                      play.quarter === 3 ? q3Ref :
                      play.quarter === 4 ? q4Ref : null;

                    return (
                      <div
                        key={idx}
                        ref={isFirstOfQuarter ? quarterRef : null}
                        className="py-3 px-3 hover:bg-[#2d4a6f]/30 rounded transition-colors border-l-2 border-[#2d4a6f]"
                      >
                        <div className="flex items-start justify-between gap-4 mb-1">
                          <div className="flex items-center gap-3">
                            <span className="text-[#94a3b8] text-xs">Q{play.quarter}</span>
                            <span className="text-[#94a3b8] text-xs">{play.time}</span>
                            <span className="inline-flex items-center justify-center bg-[#1e3a5f] text-white px-2 py-0.5 rounded text-xs">
                              {play.team_id}
                            </span>
                          </div>
                          <div className="text-right">
                            <div className="text-[#94a3b8] text-xs">{play.down_distance}</div>
                            {play.yardline !== '—' && (
                              <div className="text-[#94a3b8] text-xs">{play.yardline}</div>
                            )}
                          </div>
                        </div>
                        <p className="text-white text-sm">{play.description}</p>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-[#94a3b8] text-center py-8">No play-by-play data available.</p>
              )}
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  );
}
