<script lang="ts">
  import { getContext } from 'svelte';

  import { API_HOST, LICHESS_HOST } from './config';
  import { VARIANT_NAMES } from './consts';
  import type { SimpleModalContext } from './simple-modal';

  import type { ApiArena, ArenaEdit } from './types';
  import {
    alertErrorResponse,
    createShowSetTokenDialogFn,
    fetchTokenUser,
  } from './utils';

  export let token: string;
  export let gotoIndex: () => void;
  export let arena: ApiArena;
  export let team: string;

  let form: HTMLFormElement;

  const isTeamBattle = !!arena.teamBattle;
  let name = arena.fullName.replace(/ (Team Battle|Arena)$/g, '');
  let description = arena.description ?? '';
  let clock = arena.clock.limit / 60;
  let increment = arena.clock.increment;
  let minutes = arena.minutes;
  let variant = arena.variant;
  let rated = arena.rated;
  let position = arena.position?.fen ?? null;
  let berserkable = arena.berserkable ?? false;
  let streakable = !arena.noStreak;
  let minRating = arena?.minRating?.rating;
  let maxRating = arena?.maxRating?.rating;
  let minGames = arena?.minRatedGames?.nb;
  let minRatingEnabled = !!minRating;
  let maxRatingEnabled = !!maxRating;
  let minGamesEnabled = !!minGames;
  let startTime = new Date(arena.startsAt).toISOString().slice(0, 16);
  let teamBattleTeams = Object.entries(arena.teamBattle?.teams ?? {})
    .map(([key, name]) => `${key} "${name}"`)
    .join('\n');
  let teamBattleLeaders = arena.teamBattle?.nbLeaders;
  let msgEnabled = !!arena?.msgMinutesBefore;
  let msgMinutesBefore = arena?.msgMinutesBefore ?? 60;
  let msgTemplate = arena?.msgTemplate ?? '';

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

    const newArena: ArenaEdit = {
      id: arena.id,
      team,
      name,
      startsAt: startTime
        ? Math.round(+new Date(startTime + 'Z') / 1000)
        : undefined,
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
      isTeamBattle,
      teamBattleTeams: isTeamBattle ? teamBattleTeams : undefined,
      teamBattleLeaders: isTeamBattle ? teamBattleLeaders : undefined,
      msgMinutesBefore: msgEnabled ? msgMinutesBefore : undefined,
      msgTemplate,
    };

    try {
      const resp = await fetch(API_HOST + '/editArena', {
        method: 'POST',
        body: JSON.stringify(newArena),
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

<h2>Edit <a href="https://lihcess.org/tournament/{arena.id}">arena</a></h2>

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
        <input type="text" bind:value={name} maxlength="30" required />
        {isTeamBattle ? 'Team Battle' : 'Arena'}
      </td>
    </tr>
    <tr>
      <td>Description:<br />(optional)</td>
      <td><textarea cols="30" rows="5" bind:value={description} /></td>
    </tr>
    <tr>
      <td>Start (UTC):</td>
      <td><input type="datetime-local" bind:value={startTime} /></td>
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
          <td colspan="2">
            <span class="error">
              This team does not have a valid message token set up
            </span>
            <button on:click={() => showSetTokenDialog(team)}>
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
            <br />
            The message will be sent from the account currently logged in on this
            site.
          </small>
        </td>
      </tr>
    {/if}
  </table>
  <br />
  <button type="button" on:click={handleSave}>Save</button>
  <button type="button" on:click={gotoIndex}>Cancel</button>
</form>
