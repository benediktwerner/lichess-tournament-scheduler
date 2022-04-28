<script lang="ts">
  import {
    API_HOST,
    DEFAULT_VARIANT,
    SCHEDULE_NAMES,
    VARIANT_NAMES,
  } from './config';
  import type { Schedule } from './types';
  import { formatTime } from './utils';

  export let token: string;
  export let gotoIndex: () => void;
  export let schedule: Schedule | null = null;
  export let team: string;

  let form: HTMLFormElement;

  const create = schedule === null;
  const id = create ? 0 : schedule.id;

  const formatDatetime = (t?: number) => {
    if (!t) return t;
    return new Date(t * 1000).toISOString().slice(0, 16);
  };

  let name = schedule?.name ?? '';
  let description = schedule?.description ?? '';
  let clock = schedule?.clock ?? 3;
  let increment = schedule?.increment ?? 0;
  let minutes = schedule?.minutes ?? 60;
  let variant = schedule?.variant ?? (DEFAULT_VARIANT[team] || 'standard');
  let rated = schedule?.rated ?? true;
  let berserkable = schedule?.berserkable ?? true;
  let streakable = schedule?.streakable ?? true;
  let position = schedule?.position ?? '';
  let minRating = schedule?.minRating;
  let maxRating = schedule?.maxRating;
  let minGames = schedule?.minGames;
  let minRatingEnabled = !!minRating;
  let maxRatingEnabled = !!maxRating;
  let minGamesEnabled = !!minGames;
  const day = schedule?.scheduleDay ?? 0;
  let scheduleDay = day >= 1000 ? Math.floor(day / 1000) + 7 : day;
  let scheduleStep = day >= 1000 ? day % 1000 : 1;
  let scheduleTime = schedule ? formatTime(schedule.scheduleTime) : null;
  let scheduleStart = formatDatetime(schedule?.scheduleStart);
  let scheduleEnd = formatDatetime(schedule?.scheduleEnd);
  let scheduleStartEnabled = !!scheduleStart;
  let scheduleEndEnabled = !!scheduleEnd;
  let teamBattleTeams = schedule?.teamBattleTeams;
  let teamBattleLeaders = schedule?.teamBattleLeaders;
  let isTeamBattle = teamBattleTeams && teamBattleTeams.length > 0;

  const handleSave = async () => {
    if (!form) return;
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    const [hh, mm] = scheduleTime.split(':');
    const time = parseInt(hh) * 60 + parseInt(mm);

    const schedule: Schedule = {
      id,
      team,
      name,
      description: description || null,
      clock,
      increment,
      minutes,
      variant,
      rated,
      berserkable,
      streakable,
      position: position || null,
      minRating: minRatingEnabled && minRating ? minRating : null,
      maxRating: maxRatingEnabled && maxRating ? maxRating : null,
      minGames: minGamesEnabled && minGames ? minGames : null,
      scheduleDay:
        scheduleDay > 7 ? (scheduleDay - 7) * 1000 + scheduleStep : scheduleDay,
      scheduleTime: time,
      scheduleStart:
        (scheduleStartEnabled && scheduleStart) || scheduleDay > 7
          ? Math.floor(+new Date(scheduleStart) / 1000)
          : null,
      scheduleEnd:
        scheduleEndEnabled && scheduleEnd
          ? Math.floor(+new Date(scheduleEnd) / 1000)
          : null,
      teamBattleTeams: isTeamBattle ? teamBattleTeams : null,
      teamBattleLeaders: isTeamBattle ? teamBattleLeaders : null,
    };

    const resp = await fetch(API_HOST + (create ? '/create' : '/edit'), {
      method: 'POST',
      body: JSON.stringify(schedule),
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (resp.ok) gotoIndex();
    else alert(`Error: ${await resp.text()}`);
  };
</script>

<h2>{create ? 'Create' : 'Edit'} schedule</h2>

<form bind:this={form}>
  <table class="form-table">
    <tr>
      <td>Team:</td>
      <td
        ><a href="https://lichess.org/team/{team}" target="_blank">{team}</a
        ></td
      >
    </tr>
    <tr>
      <td>Name:</td>
      <td><input type="text" bind:value={name} required /></td>
    </tr>
    <tr>
      <td>Description:<br />(optional)</td>
      <td><textarea cols="30" rows="5" bind:value={description} /></td>
    </tr>
    <tr>
      <td>Initial clock:</td>
      <td>
        <select bind:value={clock} required>
          {#each [0, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5, 6, 7, 10, 15, 20, 25, 30, 40, 50, 60] as x}
            <option value={x}>{x}</option>
          {/each}
        </select>
        minute(s)
      </td>
    </tr>
    <tr>
      <td>Increment:</td>
      <td>
        <select bind:value={increment} required>
          {#each [0, 1, 2, 3, 4, 5, 6, 7, 10, 15, 20, 25, 30, 40, 50, 60] as x}
            <option value={x}>{x}</option>
          {/each}
        </select>
        second(s)
      </td>
    </tr>
    <tr>
      <td>Duration:</td>
      <td>
        <select bind:value={minutes} required>
          {#each [20, 25, 30, 35, 40, 45, 50, 55, 60, 70, 80, 90, 100, 110, 120, 150, 180, 210, 240, 270, 300, 330, 360, 420, 480, 540, 600, 720] as x}
            <option value={x}>{x}</option>
          {/each}
        </select>
        minute(s)
      </td>
    </tr>
    <tr>
      <td>Variant:</td>
      <td>
        <select bind:value={variant}>
          {#each Object.entries(VARIANT_NAMES) as [key, name]}
            <option value={key}>{name}</option>
          {/each}
        </select>
      </td>
    </tr>
    <tr>
      <td>Rated:</td>
      <td><input type="checkbox" bind:checked={rated} /></td>
    </tr>
    <tr>
      <td>FEN (optional):</td>
      <td
        ><input
          type="text"
          name="position"
          size="60"
          bind:value={position}
        /></td
      >
    </tr>
    <tr>
      <td>Berserkable:</td>
      <td><input type="checkbox" bind:checked={berserkable} /></td>
    </tr>
    <tr>
      <td>Streakable:</td>
      <td><input type="checkbox" bind:checked={streakable} /></td>
    </tr>
    <tr>
      <td>Min rating:</td>
      <td>
        <input type="checkbox" bind:checked={minRatingEnabled} />
        <input
          type="number"
          min="600"
          max="3000"
          step="1"
          disabled={!minRatingEnabled}
          bind:value={minRating}
        />
      </td>
    </tr>
    <tr>
      <td>Max rating:</td>
      <td>
        <input type="checkbox" bind:checked={maxRatingEnabled} />
        <input
          type="number"
          min="600"
          max="3000"
          step="1"
          disabled={!maxRatingEnabled}
          bind:value={maxRating}
        />
      </td>
    </tr>
    <tr>
      <td>Min rated games:</td>
      <td>
        <input type="checkbox" bind:checked={minGamesEnabled} />
        <input
          type="number"
          min="0"
          max="9999"
          step="1"
          disabled={!minGamesEnabled}
          bind:value={minGames}
        />
      </td>
    </tr>
    <tr>
      <td>Schedule:</td>
      <td>
        <select bind:value={scheduleDay} required>
          {#each SCHEDULE_NAMES as s, i}
            <option value={i}>{s}</option>
          {/each}
        </select>
        {#if scheduleDay > 7}
          <input
            type="number"
            min="1"
            max="999"
            step="1"
            bind:value={scheduleStep}
            required
          />
        {/if}
      </td>
    </tr>
    <tr>
      <td>Time (UTC):</td>
      <td><input type="time" bind:value={scheduleTime} required /></td>
    </tr>
    <tr>
      <td>Schedule start:</td>
      <td>
        <input
          type="checkbox"
          bind:checked={scheduleStartEnabled}
          disabled={scheduleDay > 7}
        />
        <input
          type="datetime-local"
          disabled={!scheduleStartEnabled && scheduleDay < 8}
          bind:value={scheduleStart}
          required={scheduleDay > 7}
        />
      </td>
    </tr>
    <tr>
      <td>Schedule end:</td>
      <td>
        <input type="checkbox" bind:checked={scheduleEndEnabled} />
        <input
          type="datetime-local"
          disabled={!scheduleEndEnabled}
          bind:value={scheduleEnd}
        />
      </td>
    </tr>
    <tr>
      <td>Team Battle:</td>
      <td><input type="checkbox" bind:checked={isTeamBattle} /></td>
    </tr>
    {#if isTeamBattle}
      <tr>
        <td>Teams:</td>
        <td>
          <small>(one per line, first part must be the team id)</small><br />
          <textarea cols="30" rows="5" bind:value={teamBattleTeams} required />
        </td>
      </tr>
      <tr>
        <td>Leaders:</td>
        <td>
          <input
            type="number"
            min="1"
            max="1000"
            step="1"
            bind:value={teamBattleLeaders}
            required
          />
        </td>
      </tr>
    {/if}
  </table>
  <br />
  <button type="button" on:click={handleSave}>
    {create ? 'Create' : 'Save'}
  </button>
  <button type="button" on:click={gotoIndex}>Cancel</button>
</form>
