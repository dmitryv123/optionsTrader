// src/auth/RequireAuth.tsx
import { Navigate, useLocation } from "react-router-dom";
import { token } from "../lib/token";
import type { ReactElement } from "react";

export default function RequireAuth({ children }: { children: ReactElement }) {
  const authed = token.isAuthed();
  const loc = useLocation();
  return authed ? children : <Navigate to="/login" replace state={{ from: loc }} />;
}
