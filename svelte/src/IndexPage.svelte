<script lang="ts">
  import type { Schedule, Schedules, TeamArena, TokenState } from './types';
  import { API_HOST, LICHESS_HOST } from './config';
  import {
    alertErrorResponse,
    createShowSetTokenDialogFn,
    formatDate,
    formatDuration,
    formatEndDate,
    formatTime,
    formatUntil,
  } from './utils';
  import { SCHEDULE_NAMES, TOKEN_ISSUES, VARIANT_NAMES } from './consts';
  import { getContext } from 'svelte';
  import type { SimpleModalContext } from './simple-modal';

  export let token: string;
  export let gotoCreateSchedule: (team: string) => void;
  export let gotoEditSchedule: (schedule: Schedule) => void;
  export let gotoEditArena: (id: string, team: string) => void;
  let teams: Schedules = null;
  let createdArenas: { [team: string]: TeamArena[] } = {};
  let tokenStates: Map<string, TokenState> = new Map();
  let showCreatedLoadingBtn = false;

  // {
  //   const arenas = localStorage.getItem('cachedCreatedArenas');
  //   if (arenas) createdArenas = JSON.parse(arenas);
  // }

  const createdIdsPromise = (async (): Promise<{
    [team: string]: string[];
  }> => {
    const resp = await fetch(API_HOST + '/createdUpcomingIds', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (resp.ok) {
      return await resp.json();
    } else return {};
  })();

  const loadCreatedForTeam = async (team: string) => {
    const createdIds = (await createdIdsPromise)[team];

    if (!createdIds) return;
    // if (
    //   createdArenas[team] &&
    //   createdIds.every((id) =>
    //     createdArenas[team].some((arena) => arena.id === id)
    //   )
    // ) {
    //   createdArenas[team] = createdArenas[team].filter((arena) =>
    //     createdIds.includes(arena.id)
    //   );
    //   localStorage.setItem(
    //     'cachedCreatedArenas',
    //     JSON.stringify(createdArenas)
    //   );
    //   return;
    // }

    const resp = await fetch(LICHESS_HOST + `/api/team/${team}/arena`);
    const text = await resp.text();
    const arenas = [];
    for (const line of text.split(/\r?\n/g)) {
      if (!line) continue;
      const arena = JSON.parse(line) as TeamArena;
      if (
        arena.secondsToStart &&
        arena.secondsToStart > 0 &&
        arena.system === 'arena' &&
        createdIds.includes(arena.id)
      ) {
        arenas.push(arena);
      }
    }
    createdArenas[team] = arenas;
    // localStorage.setItem('cachedCreatedArenas', JSON.stringify(createdArenas));
  };

  const fetchTokenState = async (): Promise<Map<string, TokenState>> => {
    const resp = await fetch(API_HOST + '/tokenState', {
      headers: { Authorization: `Bearer ${token}` },
    });
    const state = await resp.json();
    return new Map(Object.entries(state));
  };

  const load = async (reloadCreated: boolean) => {
    const resp = await fetch(API_HOST + '/schedules', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (resp.ok) {
      teams = await resp.json();
      if (reloadCreated) {
        try {
          tokenStates = await fetchTokenState();
        } catch (e) {
          console.error('Error while fetching tokenIssues');
          console.error(e);
        }

        if (teams!.length === 1) {
          await loadCreatedForTeam(teams![0]![0]);
        } else showCreatedLoadingBtn = true;
      }
    } else {
      await alertErrorResponse(resp);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure?')) return;
    const resp = await fetch(API_HOST + '/delete/' + id, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (resp.ok) load(false);
    else await alertErrorResponse(resp);
  };

  const handleCancel = async (team: string, id: string) => {
    if (!confirm('Are you sure?')) return;
    const resp = await fetch(API_HOST + `/cancel/${id}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (resp.ok) await loadCreatedForTeam(team);
    else await alertErrorResponse(resp);
  };

  const formatSchedule = (day: number) => {
    if (day < 8) return SCHEDULE_NAMES[day];
    const unit = ['days', 'weeks', 'months'][Math.floor(day / 1000) - 1];
    const period = day % 1000;
    return `Every ${period} ${unit}`;
  };

  const modal = getContext<SimpleModalContext>('simple-modal');
  const showSetTokenDialog = createShowSetTokenDialogFn(
    modal,
    token,
    async () => {
      tokenStates = await fetchTokenState();
    }
  );

  load(true);
</script>

{#if !teams}
  <h4>Loading ...</h4>
{:else}
  {#each teams as [team, schedules], i}
    {@const arenas = createdArenas[team]}
    {@const tokenState = tokenStates.get(team)}
    <h2>
      <a href="https://lichess.org/team/{team}" target="_blank">{team}</a>
    </h2>
    {#if tokenState && tokenState.issue}
      <span class="error">
        {TOKEN_ISSUES[tokenState.issue] ||
          `The message token for this team has an unknown issue: ${tokenState.issue}`}
      </span>
      <button on:click={() => showSetTokenDialog(team)}>
        Set a new token
      </button>
      <br />
    {:else if tokenState && tokenState.user}
      Team messages for this team are currently being sent from {tokenState.user}
      <button on:click={() => showSetTokenDialog(team)}>Change</button>
      <br />
    {/if}
    {#if arenas && arenas.length > 0}
      <h4>Created tournaments</h4>
      <table class="overview-table">
        {#each arenas as arena}
          <tr>
            <td>
              <a
                href="https://lichess.org/tournament/{arena.id}"
                target="_blank"
              >
                {arena.fullName}
              </a>
            </td>
            <td>{arena.variant.name}</td>
            <td>{arena.clock.limit / 60}+{arena.clock.increment}</td>
            <td>{formatDuration(arena.minutes)}</td>
            <td>{new Date(arena.startsAt).toUTCString()}</td>
            <td>in {formatUntil(arena.secondsToStart)}</td>
            <td>{arena.nbPlayers} players</td>
            <td>
              <button on:click={() => gotoEditArena(arena.id, team)}>
                Edit
              </button>
              <button on:click={() => handleCancel(team, arena.id)}>
                Cancel
              </button>
            </td>
          </tr>
        {/each}
      </table>
    {:else if showCreatedLoadingBtn}
      <button on:click={() => loadCreatedForTeam(team)}>Load created</button>
    {/if}
    {#if schedules.length > 0}
      <h4>Scheduled tournaments</h4>
      <table class="overview-table">
        <tr>
          <th>Name</th>
          <th>Variant</th>
          <th>TC</th>
          <th>Duration</th>
          <th>Schedule</th>
          <th>From</th>
          <th>To</th>
        </tr>
        {#each schedules as schedule}
          <tr>
            <td>
              {schedule.name}
              {schedule.teamBattleTeams ? 'Team Battle' : 'Arena'}
            </td>
            <td>{VARIANT_NAMES[schedule.variant]}</td>
            <td>{schedule.clock}+{schedule.increment}</td>
            <td>
              {formatDuration(schedule.minutes)}
            </td>
            <td>
              {formatSchedule(schedule.scheduleDay)} at {formatTime(
                schedule.scheduleTime
              )} UTC
            </td>
            <td>{formatDate(schedule.scheduleStart)}</td>
            <td>{formatEndDate(schedule.scheduleEnd)}</td>
            <td>
              <button type="button" on:click={() => gotoEditSchedule(schedule)}>
                Edit
              </button>
            </td>
            <td>
              <button type="button" on:click={() => handleDelete(schedule.id)}>
                Delete
              </button>
            </td>
          </tr>
        {/each}
      </table>
    {/if}
    <br />
    <button type="button" on:click={() => gotoCreateSchedule(team)}>
      Schedule new tournament
    </button>
    {#if i != teams.length - 1}<hr />{/if}
  {/each}
{/if}

<style lang="scss">
  hr {
    margin: 4rem 0;
  }
</style>
