<script lang="ts">
  import {
    OAuth2AuthCodePKCE,
    type AccessContext,
  } from '@bity/oauth2-auth-code-pkce';
  import Modal from 'svelte-simple-modal';
  import { API_HOST, LICHESS_HOST } from './config';
  import { API_VERSION } from './consts';
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
    scopes: ['tournament:write'],
    redirectUrl: baseUrl(),
    onAccessTokenExpiry: (refreshAccessToken) => refreshAccessToken(),
    onInvalidGrant: (_retry) => {},
  });

  const loadAccessContext = (): AccessContext | null => {
    const ctx = localStorage.getItem('token');
    return ctx ? JSON.parse(ctx) : null;
  };

  const loadUsername = async (): Promise<string> => {
    const name = localStorage.getItem('username');
    if (name) return name;

    const token = accessContext?.token?.value;
    if (!token) return '';

    const resp = await fetch(`${LICHESS_HOST}/api/account`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (resp.ok) {
      const json = await resp.json();
      const username = json['username'];
      if (username) {
        localStorage.setItem('username', username);
        return username;
      }
    } else {
      console.error(
        `Failed to fetch username: ${resp.status} ${resp.statusText}`
      );
    }

    return '';
  };

  const handleLogin = async () => {
    error = null;
    await oauth.fetchAuthorizationCode();
  };

  const handleLogout = async () => {
    const token = accessContext?.token?.value;

    localStorage.clear();
    accessContext = null;
    error = null;

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

      if (await oauth.isReturningFromAuthServer()) {
        accessContext = await oauth.getAccessToken();
        localStorage.clear();
        localStorage.setItem('token', JSON.stringify(accessContext));
        history.pushState(null, '', baseUrl());
      }

      userName = await loadUsername();
    } catch (err) {
      error = '' + err;
    }
  };

  let error: string | null = null;
  let accessContext: AccessContext | null = loadAccessContext();
  let userName = '';
  let outdated = true;
  init();
</script>

<Modal>
  <h1>Lichess Tournament Scheduler</h1>

  {#if !outdated}
    {#if accessContext?.token}
      <div class="logout">
        {userName}
        <button type="button" on:click={handleLogout}>Logout</button>
      </div>
      <Router token={accessContext.token.value} />
    {:else}
      <button type="button" on:click={handleLogin}>Login with Lichess</button>
    {/if}
  {/if}

  {#if error}
    <div class="error">{error}</div>
  {/if}
</Modal>

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
