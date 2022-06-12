export interface Schedule {
  id: number;
  name: string;
  team: string;
  clock: number;
  increment: number;
  minutes: number;
  variant: string;
  rated: boolean;
  position?: string;
  berserkable: boolean;
  streakable: boolean;
  description?: string;
  minRating?: number;
  maxRating?: number;
  minGames?: number;
  scheduleDay: number;
  scheduleTime: number;
  scheduleStart?: number;
  scheduleEnd?: number;
  teamBattleTeams?: string;
  teamBattleLeaders?: number;
  daysInAdvance?: number;
}

export type Schedules = [string, Schedule[]][] | null;

interface ArenaBase {
  id: string;
  fullName: string;
  clock: {
    increment: number;
    limit: number;
  };
  position?: {
    fen: string;
  };
  rated: boolean;
  minutes: number;
  startsAt: number;
  secondsToStart: number;
  createdBy: string;
  system: 'arena' | 'swiss';
  nbPlayers: number;
  teamBattle?: {
    teams: string[];
  };
}

export interface TeamArena extends ArenaBase {
  variant: {
    name: string;
    key: string;
  };
}

export interface ApiArena extends ArenaBase {
  description?: string;
  berserkable?: true;
  noStreak?: true;
  variant: string;
}

export interface ArenaEdit {
  id: string;
  name: string;
  team: string;
  clock: number;
  increment: number;
  minutes: number;
  variant: string;
  rated: boolean;
  position?: string;
  berserkable: boolean;
  streakable: boolean;
  description?: string;
  minRating?: number;
  maxRating?: number;
  minGames?: number;
  isTeamBattle: boolean;
  teamBattleTeams?: string;
  teamBattleLeaders?: number;
}
