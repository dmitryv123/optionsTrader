// src/pages/Login.tsx
import { useState } from "react";
import { useLogin } from "../hooks/useAuth";
import { useNavigate, useLocation, Link } from "react-router-dom";

export default function Login() {
  const [username, setU] = useState<string>("");
  const [password, setP] = useState<string>("");
  const login = useLogin();
  const nav = useNavigate();
  const loc = useLocation() as { state?: { from?: { pathname?: string } } };

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    login.mutate(
      { username, password },
      {
        onSuccess: () => {
          const dest = loc.state?.from?.pathname ?? "/app";
          nav(dest, { replace: true });
        },
      }
    );
  }

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: 12, width: 320 }}>
        <h2>Sign in</h2>
        <input
          placeholder="Username"
          value={username}
          onChange={(e) => setU(e.target.value)}
          autoComplete="username"
        />
        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setP(e.target.value)}
          autoComplete="current-password"
        />
        <button type="submit" disabled={login.isPending}>Login</button>
        {login.isError && <div style={{ color: "crimson" }}>Login failed</div>}
        <small>After login, try the protected <Link to="/app">/app</Link> page.</small>
      </form>
    </div>
  );
}
