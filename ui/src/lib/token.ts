// src/lib/token.ts
let accessMem: string | null = null;

const ACCESS_KEY = "access";
const REFRESH_KEY = "refresh";

export const token = {
  getAccess(): string | null {
    return accessMem ?? localStorage.getItem(ACCESS_KEY);
  },
  setAccess(v: string | null): void {
    accessMem = v;
    if (v) localStorage.setItem(ACCESS_KEY, v);
    else localStorage.removeItem(ACCESS_KEY);
  },
  getRefresh(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  setRefresh(v: string | null): void {
    if (v) localStorage.setItem(REFRESH_KEY, v);
    else localStorage.removeItem(REFRESH_KEY);
  },
  clear(): void {
    accessMem = null;
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
  isAuthed(): boolean {
    return !!this.getAccess() || !!this.getRefresh();
  }
};

