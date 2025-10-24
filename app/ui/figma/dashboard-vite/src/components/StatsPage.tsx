// components/StatsPage.tsx
import React, { useState, useMemo } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Settings, Search } from 'lucide-react';
import { CustomizeStatsModal } from './CustomizeStatsModal';

type TabType = 'team' | 'player' | 'coach';

interface StatsPageProps {
  // Props for data and configuration
}

export function StatsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('player');
  const [isCustomizeModalOpen, setIsCustomizeModalOpen] = useState(false);
  const [selectedStats, setSelectedStats] = useState<string[]>([
    'player_name', 'team', 'position', 'overall', 'pass_yds', 'rush_yds', 'rec_yds', 'tackles'
  ]);

  // Mock data for demonstration
  const mockData = useMemo(() => [
    { player_name: 'Josh Allen', team: 'BUF', position: 'QB', overall: 89, pass_yds: 4407, rush_yds: 524, rec_yds: 0, tackles: 0 },
    { player_name: 'Derrick Henry', team: 'TEN', position: 'RB', overall: 87, pass_yds: 0, rush_yds: 1538, rec_yds: 0, tackles: 0 },
    { player_name: 'Davante Adams', team: 'LV', position: 'WR', overall: 91, pass_yds: 0, rush_yds: 0, rec_yds: 1553, tackles: 0 },
    { player_name: 'Aaron Donald', team: 'LAR', position: 'DT', overall: 95, pass_yds: 0, rush_yds: 0, rec_yds: 0, tackles: 68 },
    { player_name: 'Travis Kelce', team: 'KC', position: 'TE', overall: 88, pass_yds: 0, rush_yds: 0, rec_yds: 1338, tackles: 0 },
  ], []);

  const renderFilterControls = () => {
    switch (activeTab) {
      case 'team':
        return (
          <div className="flex gap-4 items-center">
            <Select>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Conference (All)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="afc">AFC</SelectItem>
                <SelectItem value="nfc">NFC</SelectItem>
              </SelectContent>
            </Select>
            <Select>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Division (All)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="afc-east">AFC East</SelectItem>
                <SelectItem value="afc-north">AFC North</SelectItem>
                <SelectItem value="afc-south">AFC South</SelectItem>
                <SelectItem value="afc-west">AFC West</SelectItem>
                <SelectItem value="nfc-east">NFC East</SelectItem>
                <SelectItem value="nfc-north">NFC North</SelectItem>
                <SelectItem value="nfc-south">NFC South</SelectItem>
                <SelectItem value="nfc-west">NFC West</SelectItem>
              </SelectContent>
            </Select>
            <Input placeholder="Search team name..." className="w-64" />
            <Button variant="outline" onClick={() => setIsCustomizeModalOpen(true)}>
              <Settings className="w-4 h-4 mr-2" />
              Customize Team Stats
            </Button>
          </div>
        );
      
      case 'player':
        return (
          <div className="flex gap-4 items-center">
            <Select>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Team (All)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="buf">Buffalo Bills</SelectItem>
                <SelectItem value="ten">Tennessee Titans</SelectItem>
                <SelectItem value="lv">Las Vegas Raiders</SelectItem>
                <SelectItem value="lar">Los Angeles Rams</SelectItem>
                <SelectItem value="kc">Kansas City Chiefs</SelectItem>
              </SelectContent>
            </Select>
            <Select>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Position (All)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="qb">QB</SelectItem>
                <SelectItem value="rb">RB</SelectItem>
                <SelectItem value="wr">WR</SelectItem>
                <SelectItem value="te">TE</SelectItem>
                <SelectItem value="ol">OL</SelectItem>
                <SelectItem value="dl">DL</SelectItem>
                <SelectItem value="lb">LB</SelectItem>
                <SelectItem value="db">DB</SelectItem>
                <SelectItem value="k">K</SelectItem>
                <SelectItem value="p">P</SelectItem>
              </SelectContent>
            </Select>
            <Input placeholder="Search player name..." className="w-64" />
            <Button variant="outline" onClick={() => setIsCustomizeModalOpen(true)}>
              <Settings className="w-4 h-4 mr-2" />
              Customize Player Stats
            </Button>
          </div>
        );
      
      case 'coach':
        return (
          <div className="flex gap-4 items-center">
            <Select>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Team (All)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="buf">Buffalo Bills</SelectItem>
                <SelectItem value="ten">Tennessee Titans</SelectItem>
                <SelectItem value="lv">Las Vegas Raiders</SelectItem>
                <SelectItem value="lar">Los Angeles Rams</SelectItem>
                <SelectItem value="kc">Kansas City Chiefs</SelectItem>
              </SelectContent>
            </Select>
            <Select>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Role (All)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="hc">Head Coach</SelectItem>
                <SelectItem value="oc">Offensive Coordinator</SelectItem>
                <SelectItem value="dc">Defensive Coordinator</SelectItem>
              </SelectContent>
            </Select>
            <Input placeholder="Search coach name..." className="w-64" />
            <Button variant="outline" onClick={() => setIsCustomizeModalOpen(true)}>
              <Settings className="w-4 h-4 mr-2" />
              Customize Coach Stats
            </Button>
          </div>
        );
      
      default:
        return null;
    }
  };

  const getColumnHeaders = () => {
    const headerMap: Record<string, string> = {
      player_name: 'Player Name',
      team: 'Team',
      position: 'Pos',
      overall: 'OVR',
      pass_yds: 'Pass Yds',
      rush_yds: 'Rush Yds',
      rec_yds: 'Rec Yds',
      tackles: 'Tackles',
    };
    
    return selectedStats.map(stat => headerMap[stat] || stat);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Franchise Football Stats</h1>
      </div>

      {/* Tab Navigation */}
      <div className="mb-6">
        <div className="flex space-x-1 bg-white rounded-lg p-1 shadow-sm">
          {(['team', 'player', 'coach'] as TabType[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-3 rounded-md font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Control Bar */}
      <div className="mb-6 bg-white rounded-lg p-4 shadow-sm">
        {renderFilterControls()}
      </div>

      {/* Data Table */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                {getColumnHeaders().map((header, index) => (
                  <th
                    key={index}
                    className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${
                      index === 0 ? 'sticky left-0 bg-gray-50 z-10' : ''
                    }`}
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {mockData.map((row, rowIndex) => (
                <tr key={rowIndex} className="hover:bg-gray-50">
                  {selectedStats.map((stat, colIndex) => (
                    <td
                      key={colIndex}
                      className={`px-6 py-4 whitespace-nowrap text-sm text-gray-900 ${
                        colIndex === 0 ? 'sticky left-0 bg-white z-10 font-medium' : ''
                      }`}
                    >
                      {row[stat as keyof typeof row]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {/* Horizontal Scroll Indicator */}
        <div className="px-6 py-2 bg-gray-50 text-xs text-gray-500 text-center">
          ← Scroll horizontally to view more columns →
        </div>
      </div>

      {/* Customize Stats Modal */}
      <CustomizeStatsModal
        isOpen={isCustomizeModalOpen}
        onClose={() => setIsCustomizeModalOpen(false)}
        activeTab={activeTab}
        selectedStats={selectedStats}
        onStatsChange={setSelectedStats}
      />
    </div>
  );
}
