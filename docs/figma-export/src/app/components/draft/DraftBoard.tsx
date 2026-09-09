/**
 * Draft Board Component
 * Main draft board view with filters, prospects table, and best available
 */

import { useState, useEffect } from 'react';
import { DraftProspect, getDraftProspects, getBestAvailable, DraftFilters } from '../../lib/mockDraftApi';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select } from '../ui/select';
import { Switch } from '../ui/switch';
import { Badge } from '../ui/badge';
import { Skeleton } from '../ui/skeleton';
import { Check, ArrowUpDown } from 'lucide-react';

interface DraftBoardProps {
  onCompareClick: (prospects: DraftProspect[]) => void;
}

export function DraftBoard({ onCompareClick }: DraftBoardProps) {
  const [prospects, setProspects] = useState<DraftProspect[]>([]);
  const [bestAvailable, setBestAvailable] = useState<DraftProspect[]>([]);
  const [selectedProspects, setSelectedProspects] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<DraftFilters>({
    season: '2025',
    position: 'ALL',
    minOverall: 0,
    minPotential: 0,
    showDrafted: true,
    sortBy: 'board_score',
    sortOrder: 'desc',
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [bestAvailablePos, setBestAvailablePos] = useState<string>('ALL');
  const itemsPerPage = 20;

  useEffect(() => {
    loadData();
  }, [filters]);

  useEffect(() => {
    loadBestAvailable();
  }, [bestAvailablePos]);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await getDraftProspects(filters);
      setProspects(data);
      setCurrentPage(1);
    } catch (error) {
      console.error('Failed to load prospects:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadBestAvailable = async () => {
    try {
      const data = await getBestAvailable(15, bestAvailablePos);
      setBestAvailable(data);
    } catch (error) {
      console.error('Failed to load best available:', error);
    }
  };

  const toggleProspect = (prospectId: string) => {
    const newSelected = new Set(selectedProspects);
    if (newSelected.has(prospectId)) {
      newSelected.delete(prospectId);
    } else {
      if (newSelected.size < 5) {
        newSelected.add(prospectId);
      }
    }
    setSelectedProspects(newSelected);
  };

  const handleCompare = () => {
    const selected = prospects.filter(p => selectedProspects.has(p.prospect_id));
    onCompareClick(selected);
  };

  const paginatedProspects = prospects.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const totalPages = Math.ceil(prospects.length / itemsPerPage);

  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Left Sidebar - Filters */}
      <div className="col-span-12 lg:col-span-2">
        <div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] p-6 sticky top-24">
          <h3 className="text-white mb-4">Filters</h3>
          
          <div className="space-y-4">
            {/* Season */}
            <div>
              <Label className="text-[#94a3b8] text-sm mb-2 block">Season</Label>
              <select
                value={filters.season}
                onChange={(e) => setFilters({ ...filters, season: e.target.value })}
                className="w-full bg-[#1F2A35] border border-[#2d4a6f] rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value="2025">2025</option>
                <option value="2024">2024</option>
                <option value="2023">2023</option>
              </select>
            </div>

            {/* Position */}
            <div>
              <Label className="text-[#94a3b8] text-sm mb-2 block">Position</Label>
              <select
                value={filters.position}
                onChange={(e) => setFilters({ ...filters, position: e.target.value })}
                className="w-full bg-[#1F2A35] border border-[#2d4a6f] rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value="ALL">All Positions</option>
                <option value="QB">QB</option>
                <option value="RB">RB</option>
                <option value="WR">WR</option>
                <option value="TE">TE</option>
                <option value="OL">OL</option>
                <option value="DL">DL</option>
                <option value="LB">LB</option>
                <option value="CB">CB</option>
                <option value="S">S</option>
                <option value="K">K</option>
              </select>
            </div>

            {/* Min Overall */}
            <div>
              <Label className="text-[#94a3b8] text-sm mb-2 block">
                Min Overall ({filters.minOverall})
              </Label>
              <input
                type="range"
                min="0"
                max="99"
                value={filters.minOverall}
                onChange={(e) => setFilters({ ...filters, minOverall: Number(e.target.value) })}
                className="w-full"
              />
            </div>

            {/* Min Potential */}
            <div>
              <Label className="text-[#94a3b8] text-sm mb-2 block">
                Min Potential ({filters.minPotential})
              </Label>
              <input
                type="range"
                min="0"
                max="99"
                value={filters.minPotential}
                onChange={(e) => setFilters({ ...filters, minPotential: Number(e.target.value) })}
                className="w-full"
              />
            </div>

            {/* Show Drafted */}
            <div className="flex items-center justify-between">
              <Label className="text-[#94a3b8] text-sm">Show Drafted</Label>
              <Switch
                checked={filters.showDrafted}
                onCheckedChange={(checked) => setFilters({ ...filters, showDrafted: checked })}
              />
            </div>

            {/* Sort By */}
            <div>
              <Label className="text-[#94a3b8] text-sm mb-2 block">Sort By</Label>
              <select
                value={filters.sortBy}
                onChange={(e) => setFilters({ ...filters, sortBy: e.target.value as any })}
                className="w-full bg-[#1F2A35] border border-[#2d4a6f] rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value="board_score">Board Score</option>
                <option value="overall">Overall</option>
                <option value="potential">Potential</option>
                <option value="name">Name</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Center - Prospects Table */}
      <div className="col-span-12 lg:col-span-7">
        <div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] overflow-hidden">
          {/* Header */}
          <div className="p-6 border-b border-[#1F2A35] flex items-center justify-between">
            <div>
              <h3 className="text-white">Draft Prospects</h3>
              <p className="text-[#94a3b8] text-sm">{prospects.length} total prospects</p>
            </div>
            <div className="flex items-center gap-3">
              <Button
                onClick={handleCompare}
                disabled={selectedProspects.size < 2}
                className="bg-[#d4af37] hover:bg-[#c49a2e] text-[#0a1929] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Compare ({selectedProspects.size})
              </Button>
              <Button
                disabled={selectedProspects.size !== 1}
                className="bg-[#1e40af] hover:bg-[#1e40af]/90 text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Make Pick
              </Button>
            </div>
          </div>

          {/* Table */}
          {loading ? (
            <div className="p-6 space-y-3">
              {[...Array(10)].map((_, i) => (
                <Skeleton key={i} className="h-12 bg-[#1F2A35]" />
              ))}
            </div>
          ) : paginatedProspects.length === 0 ? (
            <div className="p-12 text-center">
              <p className="text-[#94a3b8]">No prospects found matching your filters</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-[#0B0F14] sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left text-[#94a3b8] text-xs font-semibold">
                      <div className="w-6" />
                    </th>
                    <th className="px-4 py-3 text-left text-[#94a3b8] text-xs font-semibold">Name</th>
                    <th className="px-4 py-3 text-left text-[#94a3b8] text-xs font-semibold">Pos</th>
                    <th className="px-4 py-3 text-left text-[#94a3b8] text-xs font-semibold">College</th>
                    <th className="px-4 py-3 text-right text-[#94a3b8] text-xs font-semibold">OVR</th>
                    <th className="px-4 py-3 text-right text-[#94a3b8] text-xs font-semibold">POT</th>
                    <th className="px-4 py-3 text-right text-[#94a3b8] text-xs font-semibold">SPD</th>
                    <th className="px-4 py-3 text-right text-[#94a3b8] text-xs font-semibold">AGI</th>
                    <th className="px-4 py-3 text-right text-[#94a3b8] text-xs font-semibold">STR</th>
                    <th className="px-4 py-3 text-right text-[#94a3b8] text-xs font-semibold">AWR</th>
                    <th className="px-4 py-3 text-center text-[#94a3b8] text-xs font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedProspects.map((prospect) => (
                    <tr
                      key={prospect.prospect_id}
                      onClick={() => toggleProspect(prospect.prospect_id)}
                      className={`border-t border-[#1F2A35] hover:bg-[#1a2332] cursor-pointer transition-colors ${
                        selectedProspects.has(prospect.prospect_id) ? 'bg-[#1e3a5f]/30' : ''
                      }`}
                    >
                      <td className="px-4 py-3">
                        <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                          selectedProspects.has(prospect.prospect_id)
                            ? 'bg-[#d4af37] border-[#d4af37]'
                            : 'border-[#2d4a6f]'
                        }`}>
                          {selectedProspects.has(prospect.prospect_id) && (
                            <Check className="w-3 h-3 text-[#0a1929]" />
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-white">{prospect.name}</div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="outline" className="border-[#2d4a6f] text-[#94a3b8]">
                          {prospect.position}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-[#94a3b8] text-sm">{prospect.college}</td>
                      <td className="px-4 py-3 text-right text-white">{prospect.overall}</td>
                      <td className="px-4 py-3 text-right text-white">{prospect.potential}</td>
                      <td className="px-4 py-3 text-right text-[#94a3b8] text-sm">{prospect.speed}</td>
                      <td className="px-4 py-3 text-right text-[#94a3b8] text-sm">{prospect.agility}</td>
                      <td className="px-4 py-3 text-right text-[#94a3b8] text-sm">{prospect.strength}</td>
                      <td className="px-4 py-3 text-right text-[#94a3b8] text-sm">{prospect.awareness}</td>
                      <td className="px-4 py-3 text-center">
                        {prospect.drafted ? (
                          <Badge className="bg-[#e74c3c]/20 text-[#e74c3c] border border-[#e74c3c]/30">
                            Rd {prospect.draft_round}
                          </Badge>
                        ) : (
                          <Badge className="bg-[#27ae60]/20 text-[#27ae60] border border-[#27ae60]/30">
                            Available
                          </Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {!loading && prospects.length > 0 && (
            <div className="p-4 border-t border-[#1F2A35] flex items-center justify-between">
              <div className="text-[#94a3b8] text-sm">
                Showing {(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, prospects.length)} of {prospects.length}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="bg-transparent border-[#2d4a6f] text-[#94a3b8] hover:bg-[#1a2332]"
                >
                  Previous
                </Button>
                <div className="text-white text-sm px-3">
                  Page {currentPage} of {totalPages}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="bg-transparent border-[#2d4a6f] text-[#94a3b8] hover:bg-[#1a2332]"
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right Sidebar - Best Available */}
      <div className="col-span-12 lg:col-span-3">
        <div className="bg-[#11161C] rounded-2xl border border-[#1F2A35] p-6 sticky top-24">
          <div className="mb-4">
            <h3 className="text-white mb-2">Best Available</h3>
            <select
              value={bestAvailablePos}
              onChange={(e) => setBestAvailablePos(e.target.value)}
              className="w-full bg-[#1F2A35] border border-[#2d4a6f] rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value="ALL">All Positions</option>
              <option value="QB">QB</option>
              <option value="RB">RB</option>
              <option value="WR">WR</option>
              <option value="TE">TE</option>
              <option value="OL">OL</option>
              <option value="DL">DL</option>
              <option value="LB">LB</option>
              <option value="CB">CB</option>
              <option value="S">S</option>
            </select>
          </div>

          <div className="space-y-2">
            {bestAvailable.map((prospect, index) => (
              <div
                key={prospect.prospect_id}
                className="bg-[#0B0F14] border border-[#1F2A35] rounded-lg p-3 hover:bg-[#1a2332] transition-colors cursor-pointer"
                onClick={() => toggleProspect(prospect.prospect_id)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-[#d4af37] text-[#0a1929] flex items-center justify-center text-xs">
                      {index + 1}
                    </div>
                    <div>
                      <div className="text-white text-sm">{prospect.name}</div>
                      <div className="text-[#94a3b8] text-xs">{prospect.college}</div>
                    </div>
                  </div>
                  <Badge variant="outline" className="border-[#2d4a6f] text-[#94a3b8] text-xs">
                    {prospect.position}
                  </Badge>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="text-[#94a3b8]">
                    OVR: <span className="text-white">{prospect.overall}</span>
                  </div>
                  <div className="text-[#94a3b8]">
                    POT: <span className="text-white">{prospect.potential}</span>
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
