<script lang="ts">
  import { OAuth2AuthCodePKCE } from '@bity/oauth2-auth-code-pkce';
  import { LICHESS_HOST } from './config';
  import Inner from './Inner.svelte';

  const baseUrl = () => {
    const url = new URL(location.href);
    url.search = '';
    return url.href;
  };

  const oauth = new OAuth2AuthCodePKCE({
    authorizationUrl: `${LICHESS_HOST}/oauth`,
    tokenUrl: `${LICHESS_HOST}/api/token`,
    clientId: 'tournament-scheduler',
    scopes: ['tournament:write'],
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
      const hasAuthCode = await oauth.isReturningFromAuthServer();
      if (hasAuthCode) {
        accessContext = await oauth.getAccessToken();
        localStorage.setItem('token', JSON.stringify(accessContext));
        history.pushState(null, '', baseUrl());
      }
    } catch (err) {
      error = err;
    }
  };

  let error = null;
  let accessContext = loadAccessContext();
  init();
</script>

<h1>Lichess Tournament Scheduler</h1>

{#if accessContext?.token}
  <button class="logout" type="button" on:click={handleLogout}>Logout</button>
  <Inner token={accessContext.token.value} />
{:else}
  <button type="button" on:click={handleLogin}>Login with Lichess</button>
{/if}

{#if error}
  <div class="error">{error}</div>
{/if}

<style lang="scss">
  :global {
    @import './global.scss';
  }

  .error {
    color: red;
  }

  .logout {
    position: fixed;
    top: 1em;
    right: 1em;
  }
</style>
