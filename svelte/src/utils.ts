import type { SimpleModalContext } from './simple-modal';
import SetTokenDialog from './SetTokenDialog.svelte';
import { API_HOST } from './config';

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
  if (!t) return '';
  return new Date(t * 1000).toISOString().slice(0, 10);
};

export const formatEndDate = (t?: number) => {
  if (!t) return '';
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

export const alertErrorResponse = async (resp: Response) => {
  try {
    const json = await resp.json();
    if (!json.name || !json.description)
      alert(`Error: ${JSON.stringify(json)}`);
    else alert(`Error: ${json.name}\n\n${json.description}`);
  } catch {
    alert(`Error: ${await resp.text()}`);
  }
};

export const createShowSetTokenDialogFn =
  (modal: SimpleModalContext, onSetToken: () => void) => (team: string) => {
    modal.open(
      SetTokenDialog,
      {
        setToken: async (token: string) => {
          const resp = await fetch(API_HOST + `/setToken/${team}`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
            body: JSON.stringify({ token }),
          });
          if (resp.ok) {
            modal.close();
            onSetToken();
          } else await alertErrorResponse(resp);
        },
      },
      {
        closeButton: false,
        styleContent: { padding: '24px' },
        styleWindow: {
          // background: 'var(--card-bg)',
          // color: 'var(--text)',
          width: '400px',
        },
      }
    );
  };

export const fetchTokenUser = async (team: string, token: string) => {
  const resp = await fetch(API_HOST + `/hasToken/${team}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (resp.ok) {
    const j = await resp.json();
    return j.exists;
  } else {
    console.error(
      `Failed to check token validity: ${resp.status} ${resp.statusText}`
    );
    return true;
  }
};
