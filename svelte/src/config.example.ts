export const API_HOST = IS_PRODUCTION
  ? 'https://tournament-scheduler.lichess.ovh'
  : 'http://localhost:5000';

export const LICHESS_HOST = IS_PRODUCTION
  ? 'https://lichess.org'
  : 'http://localhost:9663';

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
