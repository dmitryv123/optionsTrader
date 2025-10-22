import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosError,
} from "axios";
import { token } from "./token";

/** Extend request config locally to track our single-retry flag. */
interface RetryConfig extends AxiosRequestConfig {
  _retry?: boolean;
}

/** Base URL from env (typed as string), with a safe default for dev. */
const baseURL: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  "http://127.0.0.1:8000";

/** Shared Axios instance (plain config keeps TS happy across versions). */
export const api: AxiosInstance = axios.create({ baseURL });

/** Attach Authorization header if we have an access token. */
api.interceptors.request.use((config: AxiosRequestConfig) => {
  const access = token.getAccess();
  if (access) {
    // Normalize headers to a simple string map
    const headers = { ...(config.headers as Record<string, string> | undefined) };
    headers.Authorization = `Bearer ${access}`;
    config.headers = headers;
  }
  return config;
});

/** ---- Single-flight refresh logic (strictly typed) ---- */
let refreshing = false;
let waiters: Array<(t: string | null) => void> = [];

/** Wait for an in-flight refresh to complete. */
function waitForRefresh(): Promise<string | null> {
  return new Promise<string | null>((resolve) => {
    // Wrap to match our waiter signature exactly (no PromiseLike mismatch)
    waiters.push((t: string | null) => resolve(t));
  });
}

/** Resolve all waiters with the new access token (or null on failure). */
function resolveWaiters(value: string | null): void {
  const pending = waiters;
  waiters = [];
  for (const w of pending) w(value);
}

/** Safely set Authorization header on a config. */
function withAuth(config: RetryConfig, access: string): RetryConfig {
  const headers = { ...(config.headers as Record<string, string> | undefined) };
  headers.Authorization = `Bearer ${access}`;
  config.headers = headers;
  return config;
}

/** Refresh-once interceptor: if a request 401s, refresh and retry exactly once. */
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const { response } = error;
    const cfg = (error.config ?? {}) as RetryConfig;

    // Bail if no response, not a 401, or already retried.
    if (!response || response.status !== 401 || cfg._retry) {
      throw error;
    }

    cfg._retry = true;

    const refresh = token.getRefresh();
    if (!refresh) {
      token.clear();
      throw error;
    }

    // If another request is already refreshing, wait for it.
    if (refreshing) {
      const newAccess = await waitForRefresh();
      if (!newAccess) throw error;
      return api.request(withAuth(cfg, newAccess));
    }

    // Perform the refresh ourselves.
    try {
      refreshing = true;
      const { data } = await axios.post<{ access: string }>(
        `${baseURL}/api/auth/refresh/`,
        { refresh }
      );
      token.setAccess(data.access);
      resolveWaiters(data.access);
      return api.request(withAuth(cfg, data.access));
    } catch (refreshErr) {
      token.clear();
      resolveWaiters(null);
      throw refreshErr;
    } finally {
      refreshing = false;
    }
  }
);
