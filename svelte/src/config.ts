export const API_HOST = 'http://localhost:5000';

export const LICHESS_HOST = IS_PRODUCTION
  ? 'https://lichess.org'
  : 'http://localhost:9663';
export const API_VERSION = 3;

export const VARIANT_NAMES = {
  standard: 'Standard',
  chess960: 'Chess960',
  crazyhouse: 'Crazyhouse',
  antichess: 'Antichess',
  atomic: 'Atomic',
  horde: 'Horde',
  kingOfTheHill: 'King Of The Hill',
  racingKings: 'Racing Kings',
  threeCheck: 'Three Check',
};

export const DEFAULT_VARIANT = {
  'lichess-chess960': 'chess960',
  'lichess-crazyhouse': 'crazyhouse',
  'lichess-antichess': 'antichess',
  'lichess-atomic': 'atomic',
  'lichess-horde': 'horde',
  'lichess-king-of-hill': 'kingOfTheHill',
  'lichess-racing-kings': 'racingKings',
  'lichess-three-check': 'threeCheck',
};

export const SCHEDULE_NAMES = [
  'Every day',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
  'Every x days',
  'Every x weeks',
  'Every x months',
  'Specific weekday of each month',
];
