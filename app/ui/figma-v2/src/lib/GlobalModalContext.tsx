import { createContext, useContext, useState, ReactNode } from 'react';

interface Player {
  name: string;
  num?: number;
  pos: string;
  age: number;
  ovr: number;
  spd?: number;
  str?: number;
  agi?: number;
  tpw?: number;
  tac?: number;
  cth?: number;
  tck?: number;
  awr?: number;
  pot?: number;
  sta?: number;
  inj?: number;
  mor?: number;
  ctr?: string;
  yrs?: number;
  dep?: string;
  hlth?: string;
  trd?: boolean;
  [key: string]: any;
}

interface Coach {
  id: string;
  name: string;
  title: string;
  age: number;
  experience: number;
  salary: string;
  yearsRemaining: number;
  overallRating: number;
  reputation: number;
  background: string;
  attitude: string;
  style: string;
  offense?: string;
  defense?: string;
  focusArea?: string;
  specialty?: string;
  currentTeam?: string;
  currentRole?: string;
}

interface GlobalModalContextType {
  openPlayerModal: (player: Player) => void;
  openCoachModal: (coach: Coach) => void;
  closePlayerModal: () => void;
  closeCoachModal: () => void;
  selectedPlayer: Player | null;
  selectedCoach: Coach | null;
  isPlayerModalOpen: boolean;
  isCoachModalOpen: boolean;
}

const GlobalModalContext = createContext<GlobalModalContextType | undefined>(undefined);

export function GlobalModalProvider({ children }: { children: ReactNode }) {
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [selectedCoach, setSelectedCoach] = useState<Coach | null>(null);
  const [isPlayerModalOpen, setIsPlayerModalOpen] = useState(false);
  const [isCoachModalOpen, setIsCoachModalOpen] = useState(false);

  const openPlayerModal = (player: Player) => {
    setSelectedPlayer(player);
    setIsPlayerModalOpen(true);
  };

  const openCoachModal = (coach: Coach) => {
    setSelectedCoach(coach);
    setIsCoachModalOpen(true);
  };

  const closePlayerModal = () => {
    setIsPlayerModalOpen(false);
    // Delay clearing player to avoid visual glitch during close animation
    setTimeout(() => setSelectedPlayer(null), 200);
  };

  const closeCoachModal = () => {
    setIsCoachModalOpen(false);
    setTimeout(() => setSelectedCoach(null), 200);
  };

  return (
    <GlobalModalContext.Provider
      value={{
        openPlayerModal,
        openCoachModal,
        closePlayerModal,
        closeCoachModal,
        selectedPlayer,
        selectedCoach,
        isPlayerModalOpen,
        isCoachModalOpen,
      }}
    >
      {children}
    </GlobalModalContext.Provider>
  );
}

export function useGlobalModal() {
  const context = useContext(GlobalModalContext);
  if (context === undefined) {
    throw new Error('useGlobalModal must be used within a GlobalModalProvider');
  }
  return context;
}
