import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLogout } from "../hooks/useAuth";
import { api } from "../lib/api";

type AccountMe = {
  account_id: string;
  cash: number;
  buying_power: number;
  equity: number;
  pnl_day: number;
};

export default function AppHome() {
  const [me, setMe] = useState<AccountMe | null>(null);
  const logout = useLogout();
  const navigate = useNavigate();

  async function loadMe() {
    const { data } = await api.get<AccountMe>("/api/accounts/me/");
    setMe(data);
  }

  function doLogout() {
    logout.mutate(undefined, {
      onSuccess: () => {
        navigate("/login", { replace: true });   // 👈 bounce to login
      },
    });
  }

  return (
    <div style={{ padding: 24 }}>
      <h2>Protected Area</h2>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={loadMe}>GET /api/accounts/me/</button>
        <button onClick={doLogout} disabled={logout.isPending}>
          {logout.isPending ? "Logging out..." : "Logout"}
        </button>
      </div>
      <pre style={{ marginTop: 16, background: "#111", color: "#0f0", padding: 12 }}>
        {me ? JSON.stringify(me, null, 2) : "Click the button to fetch data."}
      </pre>
    </div>
  );
}

