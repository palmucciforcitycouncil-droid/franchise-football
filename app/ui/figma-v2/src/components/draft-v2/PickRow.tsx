import { Badge } from '../ui/badge';

interface PickRowProps {
  pick: number;
  team: {
    abbr: string;
    name: string;
    color?: string;
  };
  prospect?: {
    name: string;
    ovr: number;
    pos: string;
    college: string;
  };
  status: 'pending' | 'made';
}

export function PickRow({ pick, team, prospect, status }: PickRowProps) {
  return (
    <tr className="border-b border-[#1F2A35] hover:bg-[#1a2332]/50 transition-colors">
      {/* Pick Number */}
      <td className="py-3 px-4 text-[#94a3b8] text-sm" style={{ width: '60px' }}>
        {pick}
      </td>
      
      {/* Team */}
      <td className="py-3 px-4" style={{ width: '160px' }}>
        <div className="flex items-center gap-2">
          <div 
            className="w-6 h-6 rounded flex items-center justify-center text-xs bg-[#1e3a5f] border border-[#2d4a6f]"
            style={team.color ? { backgroundColor: team.color, borderColor: team.color } : {}}
          >
            <span className="text-white text-xs">{team.abbr}</span>
          </div>
          <span className="text-white text-sm">{team.name}</span>
        </div>
      </td>
      
      {/* Prospect Name */}
      <td className="py-3 px-4">
        {status === 'pending' ? (
          <span className="text-[#94a3b8]/40 text-sm">— — — — — — — —</span>
        ) : prospect ? (
          <div className="flex items-center gap-2">
            {team.color && (
              <div 
                className="w-1.5 h-1.5 rounded-full" 
                style={{ backgroundColor: team.color }}
              />
            )}
            <span className="text-white text-sm">{prospect.name}</span>
          </div>
        ) : null}
      </td>
      
      {/* OVR */}
      <td className="py-3 px-4 text-right" style={{ width: '64px' }}>
        {status === 'pending' ? (
          <span className="text-[#94a3b8]/40 text-sm">—</span>
        ) : prospect ? (
          <span className={`text-sm px-2 py-0.5 rounded ${
            prospect.ovr >= 90 ? 'bg-green-500/20 text-green-300' :
            prospect.ovr >= 80 ? 'bg-blue-500/20 text-blue-300' :
            prospect.ovr >= 70 ? 'bg-yellow-500/20 text-yellow-300' :
            'bg-gray-500/20 text-gray-300'
          }`}>
            {prospect.ovr}
          </span>
        ) : null}
      </td>
      
      {/* Position */}
      <td className="py-3 px-4 text-center" style={{ width: '64px' }}>
        {status === 'pending' ? (
          <span className="text-[#94a3b8]/40 text-sm">—</span>
        ) : prospect ? (
          <Badge variant="outline" className="border-[#2d4a6f] text-[#94a3b8] text-xs">
            {prospect.pos}
          </Badge>
        ) : null}
      </td>
      
      {/* College */}
      <td className="py-3 px-4 text-[#94a3b8] text-sm" style={{ width: '160px' }}>
        {status === 'pending' ? '—' : prospect?.college || '—'}
      </td>
    </tr>
  );
}
