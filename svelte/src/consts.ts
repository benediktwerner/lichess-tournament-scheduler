export const API_VERSION = 5;
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
} as Record<string, string>;
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
export const WEEKDAY_NAMES = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];

export const TOKEN_ISSUES = {
  missing:
    'This team does not have a valid message token but has scheduled team messages.',
  bad: 'The message token for this team is invalid or expired.',
  temporary:
    'The message token for this team is temporary and will eventually expire. Please set a new permanent token:',
} as Record<string, string>;
