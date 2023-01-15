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
  msgMinutesBefore?: number;
  msgTemplate?: string;
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
  secondsToStart: number;
  createdBy: string;
  system: 'arena' | 'swiss';
  nbPlayers: number;
  minRating?: {
    perf: string;
    rating: number;
  };
  maxRating?: {
    perf: string;
    rating: number;
  };
  minRatedGames: {
    perf?: string;
    nb: number;
  };
}

export interface TeamArena extends ArenaBase {
  startsAt: number;
  variant: {
    name: string;
    key: string;
  };
  teamBattle?: {
    teams: string[];
    nbLeaders: number;
  };
}

export interface ApiArena extends ArenaBase {
  description?: string;
  berserkable?: true;
  noStreak?: true;
  variant: string;
  startsAt: string;
  teamBattle?: {
    teams: {
      [name: string]: string;
    };
    nbLeaders: number;
  };
  msgMinutesBefore?: number;
  msgTemplate?: string;
}

export interface ArenaEdit {
  id: string;
  name: string;
  team: string;
  startsAt?: number;
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
  msgMinutesBefore?: number;
  msgTemplate?: string;
}

export interface TokenState {
  issue?: string;
  user?: string;
}

export interface Dict {
  [key: string]: string | undefined;
}
