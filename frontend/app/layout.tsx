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
        <AuthNav />
        {children}
      </body>
    </html>
  );
}
