export const formatTime = (time: number) => {
  const hours = Math.floor(time / 60)
    .toString()
    .padStart(2, '0');
  const mins = Math.floor(time % 60)
    .toString()
    .padStart(2, '0');
  return hours + ':' + mins;
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
