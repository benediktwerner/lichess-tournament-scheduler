<script lang="ts">
  import { API_HOST, LICHESS_HOST } from './config';

  import EditArenaPage from './EditArenaPage.svelte';

  import EditPage from './EditPage.svelte';
  import IndexPage from './IndexPage.svelte';
  import type { Schedule, ApiArena } from './types';

  export let token: string;

  const enum Page {
    Index,
    ScheduleCreate,
    ScheduleEdit,
    ArenaEdit,
  }

  let page = Page.Index;
  let team: string | null = null;
  let editSchedule: Schedule | null = null;
  let editArena: ApiArena | null = null;

  const gotoIndex = () => {
    page = Page.Index;
  };
</script>

{#if page === Page.ScheduleCreate && team}
  <EditPage {token} {team} {gotoIndex} />
{:else if page === Page.ScheduleEdit && editSchedule}
  <EditPage
    {token}
    schedule={editSchedule}
    team={editSchedule.team}
    {gotoIndex}
  />
{:else if page === Page.ArenaEdit && team && editArena}
  <EditArenaPage {token} {team} arena={editArena} {gotoIndex} />
{:else}
  <IndexPage
    {token}
    gotoCreateSchedule={(t) => {
      team = t;
      page = Page.ScheduleCreate;
    }}
    gotoEditSchedule={(schedule) => {
      editSchedule = schedule;
      page = Page.ScheduleEdit;
    }}
    gotoEditArena={async (id, t) => {
      const resp = await fetch(LICHESS_HOST + '/api/tournament/' + id, {
        headers: { 'Accept-Language': 'en', Accept: 'application/json' },
      });
      if (!resp.ok) {
        alert(`Error while fetching tournament info: ${await resp.text()}`);
        return;
      }
      const resp2 = await fetch(API_HOST + '/scheduledMsg/' + id, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp2.ok) {
        alert(`Error while fetching scheduled msg: ${await resp.text()}`);
        return;
      }
      editArena = { ...(await resp.json()), ...(await resp2.json()) };
      team = t;
      page = Page.ArenaEdit;
    }}
  />
{/if}
