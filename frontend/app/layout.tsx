import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CampusOps — Personal Academic Agent",
  description: "An AI agent that knows your academic life and proactively helps manage it.",
  icons: { icon: "/logo.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
