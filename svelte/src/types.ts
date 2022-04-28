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

export interface Arena {
  id: string;
  fullName: string;
  clock: {
    increment: number;
    limit: number;
  };
  minutes: number;
  startsAt: number;
  secondsToStart: number;
  variant: { name: string };
  createdBy: string;
  system: 'arena' | 'swiss';
  nbPlayers: number;
}

export type Schedules = [string, Schedule[]][] | null;
