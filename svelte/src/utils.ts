export const SECS_IN_DAY = 24 * 60 * 60;

export const formatTime = (time: number) => {
  const hours = Math.floor(time / 60)
    .toString()
    .padStart(2, '0');
  const mins = Math.floor(time % 60)
    .toString()
    .padStart(2, '0');
  return hours + ':' + mins;
};

export const formatDate = (t?: number) => {
  if (!t) return "";
  return new Date(t * 1000).toISOString().slice(0, 10);
};

export const formatEndDate = (t?: number) => {
  if (!t) return "";
  if (t % SECS_IN_DAY === 0) return formatDate(t - SECS_IN_DAY);
  else return formatDate(t - (t % SECS_IN_DAY));
};

export const formatUntil = (seconds: number) => {
  if (seconds > 24 * 60 * 60)
    return (seconds / 24 / 60 / 60).toFixed(1) + ' day(s)';
  if (seconds > 60 * 60) return (seconds / 60 / 60).toFixed(1) + ' hour(s)';
  if (seconds > 60) return Math.floor(seconds / 60) + ' minutes';
  return seconds + ' seconds';
};

export const formatDuration = (minutes: number) => {
  if (minutes % 60 === 0) {
    if (minutes > 60) return Math.round(minutes / 60) + ' hours';
    return '1 hour';
  }
  return minutes + ' minutes';
};

export const sleep = async (delay: number) => {
  await new Promise((resolve) => setTimeout(resolve, delay));
};
