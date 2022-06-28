<script lang="ts">
  import { API_HOST, VARIANT_NAMES } from './config';

  import type { ApiArena, ArenaEdit } from './types';

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
      startsAt: startTime ? +new Date(startTime + "Z") : undefined,
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
      isTeamBattle,
      teamBattleTeams: isTeamBattle ? teamBattleTeams : null,
      teamBattleLeaders: isTeamBattle ? teamBattleLeaders : null,
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
      else alert(`Error: ${await resp.text()}`);
    } catch (e) {
      alert(`Error: ${e}`);
    }
  };
</script>

<h2>Edit arena</h2>

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
        <small>
          (unless you also update or pause the schedule, another tournament with
          the old name will be created when you change the name)
        </small>
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
  </table>
  <br />
  <button type="button" on:click={handleSave}>Save</button>
  <button type="button" on:click={gotoIndex}>Cancel</button>
</form>
