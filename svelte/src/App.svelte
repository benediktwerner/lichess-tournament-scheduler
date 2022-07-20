<script lang="ts">
  import { OAuth2AuthCodePKCE } from '@bity/oauth2-auth-code-pkce';
  import { API_HOST, API_VERSION, LICHESS_HOST } from './config';
  import Router from './Router.svelte';

  const baseUrl = () => {
    const url = new URL(location.href);
    url.search = '';
    return url.href;
  };

  const oauth = new OAuth2AuthCodePKCE({
    authorizationUrl: `${LICHESS_HOST}/oauth`,
    tokenUrl: `${LICHESS_HOST}/api/token`,
    clientId: 'tournament-scheduler',
    scopes: ['tournament:write', 'team:write'],
    redirectUrl: baseUrl(),
    onAccessTokenExpiry: (refreshAccessToken) => refreshAccessToken(),
    onInvalidGrant: (_retry) => {},
  });

  const loadAccessContext = () => {
    const ctx = localStorage.getItem('token');
    return ctx ? JSON.parse(ctx) : null;
  };

  const handleLogin = async () => {
    error = null;
    await oauth.fetchAuthorizationCode();
  };

  const handleLogout = async () => {
    const token = accessContext?.token?.value;
    localStorage.removeItem('token');
    accessContext = undefined;
    error = undefined;

    await fetch(`${LICHESS_HOST}/api/token`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  };

  const init = async () => {
    try {
      const resp = await fetch(API_HOST + '/version');
      const ver = parseInt(await resp.text(), 10);
      if (ver > API_VERSION) {
        error =
          'The frontend is out-of-date, probably due to caching. Please do a hard-reload using Ctrl+F5 or Cmd+F5 or Ctrl+Shift+R or Cmd+Shift+R';
      } else outdated = false;

      const hasAuthCode = await oauth.isReturningFromAuthServer();
      if (hasAuthCode) {
        accessContext = await oauth.getAccessToken();
        localStorage.setItem('token', JSON.stringify(accessContext));
        localStorage.setItem('hasTeamScope', 'true');
        history.pushState(null, '', baseUrl());
      } else if (
        accessContext?.token &&
        !localStorage.getItem('hasTeamScope')
      ) {
        await handleLogout();
      }
    } catch (err) {
      error = err;
    }
  };

  let error = null;
  let accessContext = loadAccessContext();
  let outdated = true;
  init();
</script>

<h1>Lichess Tournament Scheduler</h1>

{#if !outdated}
  {#if accessContext?.token}
    <button class="logout" type="button" on:click={handleLogout}>Logout</button>
    <Router token={accessContext.token.value} />
  {:else}
    <button type="button" on:click={handleLogin}>Login with Lichess</button>
  {/if}
{/if}

{#if error}
  <div class="error">{error}</div>
{/if}

<style lang="scss">
  :global {
    @import './global.scss';
  }

  .logout {
    position: fixed;
    top: 1em;
    right: 1em;
  }
</style>
