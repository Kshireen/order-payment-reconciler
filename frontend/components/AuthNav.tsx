"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { clearTokens, getRefreshToken } from "@/lib/auth";
import { useCurrentUser } from "@/lib/useCurrentUser";

export default function AuthNav() {
  const router = useRouter();
  const { loading, username } = useCurrentUser();

  async function handleLogout() {
    const refresh = getRefreshToken();
    try {
      if (refresh) {
        await apiFetch("/api/auth/logout/", { method: "POST", body: { refresh } });
      }
    } catch {
      // token may already be expired/invalid server-side - clear local state regardless
    } finally {
      clearTokens();
    //   router.push("/login");
    window.location.href = "/login";
    }
  }

  if (loading) {
    return <nav className="topnav" />;
  }

  if (!username) {
    return (
      <nav className="topnav">
        <Link href="/login">Login</Link>
        <Link href="/signup">Sign up</Link>
      </nav>
    );
  }

  return (
    <nav className="topnav">
      <Link href="/dashboard">Dashboard</Link>
      <Link href="/upload">Upload data</Link>
      <span className="nav-user">{username}</span>
      <button onClick={handleLogout} className="logout-link">
        Logout
      </button>
    </nav>
  );
}