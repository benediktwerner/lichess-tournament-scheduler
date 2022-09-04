<script lang="ts">
  export let setToken: (token: string) => void;

  let token = '';
</script>

Test
<h2>Set Message Token</h2>

Log into the Lichess account that should send the messages, then visit<a
  href="https://lichess.org/account/oauth/token/create?scopes[]=team:write&description=Variant+Team+Tournament+Scheduler+Message+Token"
  >this page</a
>, create the token and paste it here:

<label for="token" />
<input type="text" name="token" bind:value={token} />

<button on:click={() => setToken(token)}>Set Token</button>

<style>
  h2 {
    margin-top: 0;
  }
</style>
