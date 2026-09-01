// import type { Metadata } from "next";
import Link from "next/link";
import LogoutButton from "@/components/LogoutButton";
// import "./globals.css";

import type { Metadata } from "next";
import AuthNav from "@/components/AuthNav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Reconciliation Dashboard",
  description: "Order/payment reconciliation dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {/* <nav className="topnav">
          <Link href="/dashboard">Dashboard</Link>
          <Link href="/upload">Upload data</Link>
          <Link href="/login">Login</Link>
          <Link href="/signup">Sign up</Link>
          <LogoutButton />
        </nav> */}
        <AuthNav />
        {children}
      </body>
    </html>
  );
}
