'use client';

import { useEffect, useRef, useState } from 'react';
import { setAuthToken, setAuthTokenProvider } from '../lib/api';

type Provider = 'firebase' | 'supabase' | 'clerk';
type ClerkInstance = { load: () => Promise<void>; session?: { getToken: () => Promise<string | null> } | null; openSignIn: (options?: Record<string, unknown>) => Promise<void> };
type SupabaseClient = { auth: { getSession: () => Promise<{ data: { session: { access_token: string } | null } }>; signInWithOAuth: (options: unknown) => Promise<{ error: Error | null }>; onAuthStateChange: (callback: (_event: string, session: { access_token: string } | null) => void) => unknown } };
type FirebaseUser = { getIdToken: () => Promise<string>; email?: string | null };
type FirebaseAuth = { currentUser: FirebaseUser | null; signInWithPopup: (provider: unknown) => Promise<{ user: FirebaseUser }>; onAuthStateChanged: (callback: (user: FirebaseUser | null) => void) => () => void };
type FirebaseAuthFactory = { (): FirebaseAuth; GoogleAuthProvider: new () => unknown };
type FirebaseNamespace = { apps: unknown[]; initializeApp: (config: Record<string, string>) => unknown; auth: FirebaseAuthFactory };
declare global {
  interface Window {
    firebase?: FirebaseNamespace;
    supabase?: { createClient: (url: string, key: string, options?: unknown) => SupabaseClient };
    Clerk?: new (key: string) => ClerkInstance;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '') ?? '';
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY ?? '',
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN ?? '',
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID ?? '',
};
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? '';
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '';
const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? '';

const scriptPromises = new Map<string, Promise<void>>();
function loadScript(src: string): Promise<void> {
  const existing = scriptPromises.get(src);
  if (existing) return existing;
  const promise = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Could not load the sign-in library.'));
    document.head.appendChild(script);
  });
  scriptPromises.set(src, promise);
  return promise;
}

let firebaseAuth: FirebaseAuth | null = null;
let supabaseClient: SupabaseClient | null = null;
let clerkClient: ClerkInstance | null = null;

async function getFirebaseAuth(): Promise<FirebaseAuth> {
  await loadScript('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js');
  await loadScript('https://www.gstatic.com/firebasejs/10.14.1/firebase-auth-compat.js');
  if (!window.firebase) throw new Error('Firebase SDK did not initialize.');
  if (!window.firebase.apps.length) window.firebase.initializeApp(firebaseConfig);
  firebaseAuth = window.firebase.auth();
  return firebaseAuth;
}

async function getSupabase(): Promise<SupabaseClient> {
  await loadScript('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.49.4');
  if (!window.supabase) throw new Error('Supabase SDK did not initialize.');
  if (!supabaseClient) {
    supabaseClient = window.supabase.createClient(supabaseUrl, supabaseKey, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
    });
  }
  return supabaseClient;
}

async function getClerk(): Promise<ClerkInstance> {
  await loadScript('https://cdn.jsdelivr.net/npm/@clerk/clerk-js@5/dist/clerk.browser.js');
  if (!window.Clerk) throw new Error('Clerk SDK did not initialize.');
  if (!clerkClient) {
    clerkClient = new window.Clerk(clerkKey);
    await clerkClient.load();
  }
  return clerkClient;
}

async function getProviderToken(selected: Provider): Promise<string | null> {
  if (selected === 'firebase') {
    const auth = await getFirebaseAuth();
    return auth.currentUser ? auth.currentUser.getIdToken() : null;
  }
  if (selected === 'supabase') {
    const client = await getSupabase();
    const { data } = await client.auth.getSession();
    return data.session?.access_token ?? null;
  }
  const clerk = await getClerk();
  return clerk.session ? clerk.session.getToken() : null;
}

export default function AuthPanel() {
  const [provider, setProvider] = useState<Provider | null>(null);
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState<Provider | null>(null);
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState('');
  const primaryToken = useRef<string | null>(null);
  const activeProvider = useRef<Provider | null>(null);
  const mounted = useRef(false);

  async function acceptToken(token: string, selected: Provider) {
    if (!API_URL) throw new Error('Set NEXT_PUBLIC_API_URL before enabling account sign-in.');
    const pendingRaw = window.sessionStorage.getItem('scamshield:pending-link');
    let pending: { provider: Provider; link_intent: string } | null = null;
    if (pendingRaw) {
      try { pending = JSON.parse(pendingRaw) as { provider: Provider; link_intent: string }; } catch { window.sessionStorage.removeItem('scamshield:pending-link'); }
    }
    if (pending && pending.provider === selected) {
      const linked = await fetch(`${API_URL}/api/v1/auth/complete-link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: selected, identity_token: token, link_intent: pending.link_intent }),
      });
      window.sessionStorage.removeItem('scamshield:pending-link');
      if (!linked.ok) {
        const body = await linked.json().catch(() => ({}));
        throw new Error(body.detail ?? 'Could not link this provider account.');
      }
      setMessage(`Linked ${selected} to the existing ScamShield account.`);
    } else {
      const session = await fetch(`${API_URL}/api/v1/auth/session`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!session.ok) {
        const body = await session.json().catch(() => ({}));
        throw new Error(body.detail ?? 'The API could not verify this account.');
      }
      const result = await session.json();
      setEmail(result.email ?? '');
      setMessage(`Connected with ${selected === 'firebase' ? 'Firebase' : selected === 'supabase' ? 'Supabase' : 'Clerk'}.`);
    }
    primaryToken.current = token;
    activeProvider.current = selected;
    setAuthToken(token);
    setAuthTokenProvider(async () => {
      const current = activeProvider.current;
      return current ? getProviderToken(current) : null;
    });
    setProvider(selected);
    window.dispatchEvent(new Event('scamshield-auth-changed'));
  }

  async function prepareLink(selected: Provider) {
    const currentProvider = activeProvider.current;
    if (!currentProvider || currentProvider === selected) return;
    const currentToken = await getProviderToken(currentProvider);
    if (!currentToken) throw new Error('The current sign-in session has expired. Sign in again before linking another provider.');
    primaryToken.current = currentToken;
    setAuthToken(currentToken);
    const response = await fetch(`${API_URL}/api/v1/auth/link-intent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${currentToken}` },
      body: JSON.stringify({ provider: selected }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail ?? 'Could not start secure account linking.');
    }
    const result = await response.json();
    window.sessionStorage.setItem('scamshield:pending-link', JSON.stringify({
      provider: selected,
      link_intent: result.link_intent,
    }));
  }

  async function signIn(selected: Provider) {
    setBusy(selected);
    setMessage('');
    try {
      await prepareLink(selected);
      if (selected === 'firebase') {
        if (!firebaseConfig.apiKey || !firebaseConfig.authDomain || !firebaseConfig.projectId) throw new Error('Firebase public configuration is missing.');
        const auth = await getFirebaseAuth();
        const result = await auth.signInWithPopup(new (window.firebase!.auth.GoogleAuthProvider)());
        await acceptToken(await result.user.getIdToken(), selected);
      } else if (selected === 'supabase') {
        if (!supabaseUrl || !supabaseKey) throw new Error('Supabase public configuration is missing.');
        const client = await getSupabase();
        const { data } = await client.auth.getSession();
        if (data.session?.access_token) {
          await acceptToken(data.session.access_token, selected);
        } else {
          const result = await client.auth.signInWithOAuth({
            provider: 'google',
            options: { redirectTo: window.location.origin },
          });
          if (result.error) throw result.error;
        }
      } else {
        if (!clerkKey) throw new Error('Clerk publishable key is missing.');
        const clerk = await getClerk();
        if (clerk.session) {
          const token = await clerk.session.getToken();
          if (token) await acceptToken(token, selected);
        } else {
          await clerk.openSignIn({ forceRedirectUrl: window.location.href });
          const refreshedSession = (clerk as ClerkInstance).session;
          if (refreshedSession) {
            const token = await refreshedSession.getToken();
            if (token) await acceptToken(token, selected);
          }
        }
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Sign-in could not be completed.');
    } finally {
      setBusy(null);
    }
  }

  useEffect(() => {
    if (mounted.current) return;
    mounted.current = true;
    let active = true;
    async function restoreSessions() {
      try {
        const defaultOrder: Provider[] = ['supabase', 'firebase', 'clerk'];
        let pendingProvider: Provider | null = null;
        const pendingRaw = window.sessionStorage.getItem('scamshield:pending-link');
        if (pendingRaw) {
          try { pendingProvider = (JSON.parse(pendingRaw) as { provider: Provider }).provider; } catch { window.sessionStorage.removeItem('scamshield:pending-link'); }
        }
        const order = pendingProvider
          ? [pendingProvider, ...defaultOrder.filter((item) => item !== pendingProvider)]
          : defaultOrder;

        for (const candidate of order) {
          if (candidate === 'supabase' && supabaseUrl && supabaseKey) {
            const client = await getSupabase();
            const { data } = await client.auth.getSession();
            if (active && data.session?.access_token) {
              await acceptToken(data.session.access_token, 'supabase');
              return;
            }
          }
          if (candidate === 'firebase' && firebaseConfig.apiKey && firebaseConfig.authDomain && firebaseConfig.projectId) {
            const auth = await getFirebaseAuth();
            const currentUser = await new Promise<FirebaseUser | null>((resolve) => {
              let unsubscribe: () => void = () => {};
              unsubscribe = auth.onAuthStateChanged((user) => {
                unsubscribe();
                resolve(user);
              });
            });
            if (active && currentUser) {
              await acceptToken(await currentUser.getIdToken(), 'firebase');
              return;
            }
          }
          if (candidate === 'clerk' && clerkKey) {
            const clerk = await getClerk();
            if (active && clerk.session) {
              const token = await clerk.session.getToken();
              if (token) {
                await acceptToken(token, 'clerk');
                return;
              }
            }
          }
        }
      } catch {
        // A missing or expired provider session should not block public scanning.
      } finally {
        if (active) setReady(true);
      }
    }
    void restoreSessions();
    return () => { active = false; };
  }, []);

  return (
    <aside className="auth-dock" aria-label="ScamShield account sign-in">
      <div className="auth-dock-heading">
        <span className="auth-lock">✦</span>
        <span><strong>{provider ? 'Account connected' : 'Save your scans'}</strong><small>{provider ? (email || `Signed in with ${provider}`) : 'Choose a secure sign-in provider'}</small></span>
      </div>
      <div className="auth-provider-list">
        <button type="button" onClick={() => signIn('firebase')} disabled={busy !== null || !ready}>{busy === 'firebase' ? 'Connecting…' : 'Continue with Firebase'}</button>
        <button type="button" onClick={() => signIn('supabase')} disabled={busy !== null || !ready}>{busy === 'supabase' ? 'Connecting…' : 'Continue with Supabase'}</button>
        <button type="button" onClick={() => signIn('clerk')} disabled={busy !== null || !ready}>{busy === 'clerk' ? 'Connecting…' : 'Continue with Clerk'}</button>
      </div>
      {message && <p className="auth-message" role="status">{message}</p>}
      <small className="auth-caption">Link another provider while signed in to keep one ScamShield history.</small>
    </aside>
  );
}
