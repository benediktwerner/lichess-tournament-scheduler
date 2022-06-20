<script lang="ts">
  import type { Schedule, Schedules, TeamArena } from './types';
  import {
    API_HOST,
    LICHESS_HOST,
    SCHEDULE_NAMES,
    VARIANT_NAMES,
  } from './config';
  import {
    formatDate,
    formatDuration,
    formatEndDate,
    formatTime,
    formatUntil,
    sleep,
  } from './utils';

  export let token: string;
  export let gotoCreateSchedule: (team: string) => void;
  export let gotoEditSchedule: (schedule: Schedule) => void;
  export let gotoEditArena: (id: string, team: string) => void;
  let teams: Schedules = null;
  let createdArenas: { [team: string]: TeamArena[] } = {};

  const createdIdsPromise = (async () => {
    const resp = await fetch(API_HOST + '/createdUpcomingIds', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (resp.ok) {
      const json = await resp.json();
      return new Set(json as string[]);
    } else return new Set<string>();
  })();

  const loadCreatedForTeam = async (team: string) => {
    const resp = await fetch(LICHESS_HOST + `/api/team/${team}/arena`);
    const text = await resp.text();
    const createdIds = await createdIdsPromise;
    const arenas = [];
    for (const line of text.split(/\r?\n/g)) {
      if (!line) continue;
      const arena = JSON.parse(line) as TeamArena;
      if (
        arena.secondsToStart &&
        arena.secondsToStart > 0 &&
        arena.system === 'arena' &&
        createdIds.has(arena.id)
      ) {
        arenas.push(arena);
      }
    }
    createdArenas[team] = arenas;
  };

  const load = async (reloadCreated: boolean) => {
    const resp = await fetch(API_HOST + '/schedules', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (resp.ok) {
      teams = await resp.json();
      if (reloadCreated) {
        let promise = Promise.resolve();
        for (const [team, _] of teams) {
          promise = promise
            .then(() => loadCreatedForTeam(team))
            .then(() => sleep(250));
        }
        await promise;
      }
    } else {
      alert(`Error: ${await resp.text()}`);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure?')) return;
    const resp = await fetch(API_HOST + '/delete/' + id, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (resp.ok) load(false);
    else alert(`Error: ${await resp.text()}`);
  };

  const handleCancel = async (team: string, id: string) => {
    if (!confirm('Are you sure?')) return;
    const resp = await fetch(API_HOST + `/cancel/${id}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (resp.ok) await loadCreatedForTeam(team);
    else alert(`Error: ${await resp.text()}`);
  };

  const formatSchedule = (day: number) => {
    if (day < 8) return SCHEDULE_NAMES[day];
    const unit = ['days', 'weeks', 'months'][Math.floor(day / 1000) - 1];
    const period = day % 1000;
    return `Every ${period} ${unit}`;
  };

  load(true);
</script>

{#if !teams}
  <h4>Loading ...</h4>
{:else}
  {#each teams as [team, schedules], i}
    <h2>
      <a href="https://lichess.org/team/{team}" target="_blank">{team}</a>
    </h2>
    {#if createdArenas[team] && createdArenas[team].length > 0}
      <h4>Created tournaments</h4>
      <table class="overview-table">
        {#each createdArenas[team] as arena}
          <tr>
            <td><a href="https://lichess.org/tournament/{arena.id}" target="_blank">{arena.fullName}</a></td>
            <td>{arena.variant.name}</td>
            <td>{arena.clock.limit / 60}+{arena.clock.increment}</td>
            <td>{formatDuration(arena.minutes)}</td>
            <td>{new Date(arena.startsAt).toUTCString()}</td>
            <td>in {formatUntil(arena.secondsToStart)}</td>
            <td>{arena.nbPlayers} players</td>
            <td>
              <button on:click={() => gotoEditArena(arena.id, team)}>Edit</button>
              <button on:click={() => handleCancel(team, arena.id)}>
                Cancel
              </button>
            </td>
          </tr>
        {/each}
      </table>
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
