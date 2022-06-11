<script lang="ts">
  import EditPage from './EditPage.svelte';
  import IndexPage from './IndexPage.svelte';
  import type { Schedule } from './types';

  export let token: string;

  const enum Page {
    Index,
    Create,
    Edit,
  }

  let page = Page.Index;
  let createTeam: string | null = null;
  let editSchedule: Schedule | null = null;

  const gotoIndex = () => {
    page = Page.Index;
  };
</script>

{#if page === Page.Create}
  <EditPage {token} team={createTeam} {gotoIndex} />
{:else if page === Page.Edit}
  <EditPage {token} schedule={editSchedule} team={editSchedule.team} {gotoIndex} />
{:else}
  <IndexPage
    {token}
    gotoCreate={(team) => {
      createTeam = team;
      page = Page.Create;
    }}
    gotoEdit={(schedule) => {
      editSchedule = schedule;
      page = Page.Edit;
    }}
  />
{/if}
