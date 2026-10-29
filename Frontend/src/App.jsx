import { useCallback, useState } from "react";
import CashCast, { DashboardPreview } from "./CashCast.jsx";

export default function App() {
  const [auth, setAuth] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem("cashcast.auth") || "null"); }
    catch { return null; }
  });

  const signOut = useCallback(() => {
    sessionStorage.removeItem("cashcast.auth");
    setAuth(null);
  }, []);

  if (!auth?.access_token) {
    return <CashCast onOpenDashboard={(session) => {
      sessionStorage.setItem("cashcast.auth", JSON.stringify(session));
      setAuth(session);
    }} />;
  }

  return <DashboardPreview expanded role={auth.role} email={auth.email} token={auth.access_token} onSignOut={signOut} />;
}
