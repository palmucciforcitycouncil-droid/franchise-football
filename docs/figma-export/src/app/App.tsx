import { useState } from "react";
import { DivisionStandings } from "./components/DivisionStandings";
import { TeamSchedule } from "./components/TeamSchedule";
import { ScoutingPanel } from "./components/ScoutingPanel";
import { LeaguePowerRankings } from "./components/LeaguePowerRankings";
import { LeagueTopPerformers } from "./components/LeagueTopPerformers";
import { BoxScore } from "./components/BoxScore";
import { TeamTopPerformers } from "./components/TeamTopPerformers";
import { WeeklyGameplanBox } from "./components/WeeklyGameplanBox";
import { PlayByPlay } from "./components/PlayByPlay";
import { RosterPage } from "./components/RosterPage";
import { PlayoffsPage } from "./components/PlayoffsPage";
import { DraftPage } from "./components/DraftPage";
import { DraftPageV2 } from "./components/DraftPageV2";
import { GMDeskPage } from "./components/GMDeskPage";
import { StaffPage } from "./components/StaffPage";
import { StatsPage } from "./components/StatsPage";
import { HOFPage } from "./components/HOFPage";
import { Button } from "./components/ui/button";
import { Toaster } from "sonner@2.0.3";
import { GlobalModalProvider } from "./lib/GlobalModalContext";
import { PlayerCardModal } from "./components/modals/PlayerCardModal";
import { CoachCardModal } from "./components/modals/CoachCardModal";

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");

  const navItems = [
    { id: "dashboard", label: "Dashboard" },
    { id: "roster", label: "Roster" },
    { id: "staff", label: "Staff" },
    { id: "gm-desk", label: "GM Desk" },
    { id: "draft", label: "Draft" },
    { id: "playoffs", label: "Playoffs" },
    { id: "stats", label: "Stats" },
    { id: "hof", label: "HOF" },
  ];

  return (
    <GlobalModalProvider>
      <div className="min-h-screen bg-[#0a1929]">
        {/* Sticky Header - Team Info & Controls */}
        <header className="sticky top-0 z-50 bg-[#1e3a5f] border-b border-[#2d4a6f]">
          <div className="max-w-[1920px] mx-auto px-6 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="bg-[#0a1929] px-3 py-1.5 rounded border border-[#d4af37]">
                  <span className="text-white">NE</span>
                </div>
                <div>
                  <h2 className="text-white">
                    New England Patriots
                  </h2>
                  <p className="text-[#94a3b8] text-sm">
                    Record: 10-7 · AFC East · Power Rank: 8th
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  className="bg-transparent border-[#d4af37] text-[#d4af37] hover:bg-[#d4af37]/10"
                >
                  Sim Week
                </Button>
              </div>
            </div>
          </div>
        </header>

        {/* Navigation Bar */}
        <nav className="sticky top-[73px] z-40 bg-[#152238] border-b border-[#2d4a6f]">
          <div className="max-w-[1920px] mx-auto px-6">
            <div className="flex items-center gap-1">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`px-4 py-3 transition-colors relative ${
                    activeTab === item.id
                      ? "text-white bg-[#1e3a5f]"
                      : "text-[#94a3b8] hover:text-white hover:bg-[#1a2f4a]"
                  }`}
                >
                  {item.label}
                  {activeTab === item.id && (
                    <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#d4af37]" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <div className="max-w-[1920px] mx-auto px-6 py-6">
          {activeTab === "dashboard" ? (
            <div>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Row 1: Three equal-height columns */}
                {/* Column 1 - Left */}
                <div>
                  <WeeklyGameplanBox />
                </div>

                {/* Column 2 - Middle */}
                <div>
                  <TeamSchedule />
                </div>

                {/* Column 3 - Right */}
                <div>
                  <ScoutingPanel />
                </div>

                {/* Column 1 - Continued (Division Standings, League Power Rankings, Top Performers, Team Top Performers) */}
                <div className="lg:row-start-2 lg:row-span-2 space-y-6">
                  <DivisionStandings />
                  <LeaguePowerRankings />
                  <LeagueTopPerformers />
                  <TeamTopPerformers />
                </div>

                {/* Row 2: Box Score - Spans C2 & C3 */}
                <div className="lg:col-start-2 lg:col-span-2 lg:row-start-2">
                  <BoxScore />
                </div>

                {/* Row 3: Play-by-Play - Spans C2 & C3 */}
                <div className="lg:col-start-2 lg:col-span-2 lg:row-start-3">
                  <PlayByPlay />
                </div>
              </div>
            </div>
          ) : activeTab === "roster" ? (
            <RosterPage />
          ) : activeTab === "staff" ? (
            <StaffPage />
          ) : activeTab === "playoffs" ? (
            <PlayoffsPage />
          ) : activeTab === "draft" ? (
            <DraftPageV2 />
          ) : activeTab === "gm-desk" ? (
            <GMDeskPage />
          ) : activeTab === "stats" ? (
            <StatsPage />
          ) : activeTab === "hof" ? (
            <HOFPage />
          ) : (
            /* Coming Soon Pages */
            <div className="bg-[#1a2332] rounded-lg border border-[#2d4a6f] p-12 text-center">
              <div className="max-w-md mx-auto">
                <div className="w-16 h-16 bg-[#d4af37]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-8 h-8 text-[#d4af37]"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                    />
                  </svg>
                </div>
                <h2 className="text-white mb-2 capitalize">
                  {activeTab.replace("-", " ")}
                </h2>
                <p className="text-[#94a3b8]">
                  This feature is coming soon. Check back later!
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Global Modals */}
        <PlayerCardModal />
        <CoachCardModal />

        <Toaster position="top-right" richColors theme="dark" />
      </div>
    </GlobalModalProvider>
  );
}