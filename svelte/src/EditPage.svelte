<script lang="ts">
  import { getContext } from 'svelte';

  import { API_HOST, DEFAULT_VARIANT, LICHESS_HOST } from './config';
  import { SCHEDULE_NAMES, VARIANT_NAMES } from './consts';
  import type { SimpleModalContext } from './simple-modal';
  import type { Schedule, Dict } from './types';
  import {
    alertErrorResponse,
    createShowSetTokenDialogFn,
    fetchTokenUser,
    formatDate,
    formatEndDate,
    formatTime,
    SECS_IN_DAY,
  } from './utils';

  export let token: string;
  export let gotoIndex: () => void;
  export let schedule: Schedule | null = null;
  export let team: string;

  let form: HTMLFormElement;

  const [create, id] = schedule === null ? [true, 0] : [false, schedule.id];

  let name = schedule?.name ?? '';
  let description = schedule?.description ?? '';
  let clock = schedule?.clock ?? 3;
  let increment = schedule?.increment ?? 0;
  let minutes = schedule?.minutes ?? 60;
  let variant =
    schedule?.variant ?? ((DEFAULT_VARIANT as Dict)[team] || 'standard');
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
  let scheduleDay =
    day >= 10_000 ? 11 : day >= 1000 ? Math.floor(day / 1000) + 7 : day;
  let scheduleStep = day >= 1000 ? day % 1000 : 1;
  let scheduleWeekday = day >= 10_000 ? day % 10 : 0;
  let scheduleWeekdayOrdinal = day >= 10_000 ? Math.floor((day % 100) / 10) : 0;
  let scheduleTime = schedule ? formatTime(schedule.scheduleTime) : null;
  let scheduleStart = formatDate(schedule?.scheduleStart);
  let scheduleEnd = formatEndDate(schedule?.scheduleEnd);
  let scheduleStartEnabled = !!scheduleStart;
  let scheduleEndEnabled = !!scheduleEnd;
  let teamBattleTeams = schedule?.teamBattleTeams;
  let teamBattleLeaders = schedule?.teamBattleLeaders;
  let isTeamBattle = !!teamBattleTeams && teamBattleTeams.length > 0;
  let daysInAdvance = schedule?.daysInAdvance ?? 1;
  let updateCreated = false;
  let msgEnabled = !!schedule?.msgMinutesBefore;
  let msgMinutesBefore = schedule?.msgMinutesBefore ?? 60;
  let msgTemplate = schedule?.msgTemplate ?? '';

  let tokenUser: string | null = null;

  const updateTokenUser = async () => {
    tokenUser = await fetchTokenUser(team, token);
  };

  updateTokenUser();

  const modal = getContext<SimpleModalContext>('simple-modal');
  const showSetTokenDialog = createShowSetTokenDialogFn(
    modal,
    token,
    updateTokenUser
  );

  const handleSave = async () => {
    if (!form) return;
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    if (!scheduleTime) return alert('Invalid time');
    const [hh, mm] = scheduleTime.split(':');
    if (!hh || !mm) return alert('Invalid time');
    const time = parseInt(hh) * 60 + parseInt(mm);

    const schedule: Schedule & { updateCreated: boolean } = {
      id,
      team,
      name,
      description: description || undefined,
      clock,
      increment,
      minutes,
      variant,
      rated,
      berserkable,
      streakable,
      position: position || undefined,
      minRating: minRatingEnabled && minRating ? minRating : undefined,
      maxRating: maxRatingEnabled && maxRating ? maxRating : undefined,
      minGames: minGamesEnabled && minGames ? minGames : undefined,
      scheduleDay:
        scheduleDay === 11
          ? 10_000 + scheduleWeekdayOrdinal * 10 + scheduleWeekday
          : scheduleDay > 7
          ? (scheduleDay - 7) * 1000 + scheduleStep
          : scheduleDay,
      scheduleTime: time,
      scheduleStart:
        (scheduleStartEnabled && scheduleStart) ||
        (scheduleDay > 7 && scheduleDay < 11)
          ? Math.floor(+new Date(scheduleStart) / 1000)
          : undefined,
      scheduleEnd:
        scheduleEndEnabled && scheduleEnd
          ? Math.floor(+new Date(scheduleEnd) / 1000) + SECS_IN_DAY
          : undefined,
      teamBattleTeams: isTeamBattle ? teamBattleTeams : undefined,
      teamBattleLeaders: isTeamBattle ? teamBattleLeaders : undefined,
      daysInAdvance,
      updateCreated,
      msgMinutesBefore: msgEnabled ? msgMinutesBefore : undefined,
      msgTemplate,
    };

    try {
      const resp = await fetch(API_HOST + (create ? '/create' : '/edit'), {
        method: 'POST',
        body: JSON.stringify(schedule),
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (resp.ok) gotoIndex();
      else await alertErrorResponse(resp);
    } catch (e) {
      alert(`Error: ${e}`);
    }
  };
</script>

<h2>{create ? 'Create' : 'Edit'} schedule</h2>

<form bind:this={form}>
  <table class="form-table">
    <tr>
      <td>Team:</td>
      <td>
        <a href="https://lichess.org/team/{team}" target="_blank">{team}</a>
      </td>
    </tr>
    <tr>
      <td>Name:</td>
      <td>
        <input type="text" bind:value={name} required />
        {isTeamBattle ? 'Team Battle' : 'Arena'}
        <br />
        <small>
          Use <code>{'{month}'}</code> to insert the month in which the arena
          takes place.
          <br />
          Use <code>{'{weekOfMonth}'}</code> to insert the number of the week
          inside the month that the tournament takes place in. Use
          <code>{'{weekOfMonth|Final}'}</code>
          to insert "Final" (can be replaced with any arbitrary string) if it's the
          last week of the month. Use
          <code>{'{weekOfMonth|1st|2nd|3rd|4th|Final}'}</code>
          to insert "1st" for the first week etc. A "week" in this context just means
          any 7 days in a row i.e. the first week are the first 7 days of the month
          and the last are the last 7 days. This means the first/last of each weekday
          in the month will be in the first/last week by this definition.
          <br />
          Use <code>{'{n}'}</code> to insert the number this tournament has in
          the series. Use <code>{'{nth}'}</code> to insert it as an ordinal i.e.
          including the `rd` in `3rd`. Use <code>{'{n+5}'}</code> and
          <code>{'{nth+5}'}</code> if there have already been 5 previous tournaments
          created via other means.
        </small>
      </td>
    </tr>
    <tr>
      <td>Description:<br />(optional)</td>
      <td>
        <textarea cols="50" rows="10" bind:value={description} />
        <br />
        <small>
          Use <code>prev</code> and <code>next</code> as the "URL" in a markdown
          link to automatically link to the previous/next tournament of this
          series: <code>[Next tournament](next)</code>
          <br />
          Use <code>{'{name}'}</code> to insert the name of the tournament. You
          can also use <code>{'{month}'}</code>, <code>{'{weekOfMonth}'}</code>,
          <code>{'{n}'}</code>, and
          <code>{'{nth}'}</code> as above.
        </small>
      </td>
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
    {#if variant === 'standard'}
      <tr>
        <td>FEN (optional):</td>
        <td>
          <input type="text" name="position" size="60" bind:value={position} />
        </td>
      </tr>
    {/if}
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
        {#if scheduleDay > 7 && scheduleDay < 11}
          <input
            type="number"
            min="1"
            max="999"
            step="1"
            bind:value={scheduleStep}
            required
          />
        {/if}
        {#if scheduleDay === 11}
          <select bind:value={scheduleWeekdayOrdinal} required>
            <option value={0}>First</option>
            <option value={1}>Second</option>
            <option value={2}>Third</option>
            <option value={3}>Fourth</option>
            <option value={4}>Last</option>
          </select>
          <select bind:value={scheduleWeekday} required>
            <option value={0}>Monday</option>
            <option value={1}>Tuesday</option>
            <option value={2}>Wednesday</option>
            <option value={3}>Thursday</option>
            <option value={4}>Friday</option>
            <option value={5}>Saturday</option>
            <option value={6}>Sunday</option>
          </select>
        {/if}
      </td>
    </tr>
    <tr>
      <td>Time (UTC):</td>
      <td><input type="time" bind:value={scheduleTime} required /></td>
    </tr>
    <tr>
      <td
        >{scheduleDay < 8 || scheduleDay === 11
          ? 'Schedule start'
          : 'Starting from'}:</td
      >
      <td>
        {#if scheduleDay < 8 || scheduleDay === 11}
          <input type="checkbox" bind:checked={scheduleStartEnabled} />
        {/if}
        <input
          type="date"
          disabled={!scheduleStartEnabled &&
            (scheduleDay < 8 || scheduleDay === 11)}
          bind:value={scheduleStart}
          required={scheduleDay > 7 && scheduleDay < 11}
        />
        {#if scheduleDay < 8 || scheduleDay === 11}
          <small>
            (if enabled, only schedule tournaments that will start on this day
            or later)
          </small>
        {/if}
      </td>
    </tr>
    <tr>
      <td>Schedule end:</td>
      <td>
        <input type="checkbox" bind:checked={scheduleEndEnabled} />
        <input
          type="date"
          disabled={!scheduleEndEnabled}
          bind:value={scheduleEnd}
        />
        <small>
          (if enabled, only schedule tournaments that will start on this day or
          earlier)
        </small>
      </td>
    </tr>
    <tr>
      <td>Create:</td>
      <td>
        <input
          type="number"
          min="1"
          max="1000"
          step="1"
          bind:value={daysInAdvance}
          required
        /> day(s) before start
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
          <small
            >(one per line, first part must be the team id or team page URL,
            rest of the line is ignored so you can copy from the Lichess team
            battle editor which has auto-complete)</small
          ><br />
          <textarea cols="50" rows="10" bind:value={teamBattleTeams} required />
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
    <tr>
      <td> Message: </td>
      <td>
        <input type="checkbox" bind:checked={msgEnabled} />
        <small>
          (send reminder team message before the tournament starts)
        </small>
      </td>
    </tr>
    {#if msgEnabled}
      {#if tokenUser}
        <tr>
          <td>Sender:</td>
          <td><a href={`${LICHESS_HOST}/@/${tokenUser}`}>@{tokenUser}</a></td>
        </tr>
      {:else}
        <tr>
          <td />
          <td>
            <span class="error">
              This team does not have a valid message token set up
            </span>
            <button type="button" on:click={() => showSetTokenDialog(team)}>
              Set a token
            </button>
          </td>
        </tr>
      {/if}
      <tr>
        <td />
        <td>
          <input
            type="number"
            bind:value={msgMinutesBefore}
            min="10"
            required
          />
          minutes before start
          <br />
          <br />
          <textarea cols="60" rows="10" bind:value={msgTemplate} required />
          <br />
          <small>
            Use <code>{'{link}'}</code> to insert a link to the tournament.
          </small>
        </td>
      </tr>
    {/if}
  </table>
  {#if !create}
    <hr />
    <table class="form-table">
      <tr>
        <td>Update already created tournaments:</td>
        <td>
          <input type="checkbox" bind:checked={updateCreated} />
        </td>
      </tr>
    </table>
  {/if}
  <br />
  <button type="button" on:click={handleSave}>
    {create ? 'Create' : 'Save'}
  </button>
  <button type="button" on:click={gotoIndex}>Cancel</button>
</form>

<style>
  td {
    padding-bottom: 8px;
  }
</style>
