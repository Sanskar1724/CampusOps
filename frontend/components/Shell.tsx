"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";

const LINKS = [
  ["Dashboard", "/dashboard"],
  ["AI Chat", "/chat"],
  ["Timetable", "/timetable"],
  ["Email", "/email"],
  ["Documents", "/documents"],
  ["Planner", "/tasks"],
  ["Notifications", "/notifications"],
  ["Profile", "/profile"],
  ["Settings", "/settings"],
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  return (
    <div className="min-h-screen flex">
      <aside className="w-56 shrink-0 border-r border-slate-200 bg-white p-4 hidden md:block">
        <Link href="/dashboard" className="block px-3 py-2 mb-4">
          <span className="text-lg font-bold text-indigo-700">CampusOps</span>
          <span className="block text-xs text-slate-500">Personal Academic Agent</span>
        </Link>
        <nav className="space-y-1">
          {LINKS.map(([label, href]) => (
            <Link
              key={href}
              href={href}
              className={`navlink ${path === href ? "navlink-active" : ""}`}
            >
              {label}
            </Link>
          ))}
        </nav>
        <button
          className="btn-ghost w-full mt-6"
          onClick={() => {
            clearToken();
            router.push("/login");
          }}
        >
          Sign out
        </button>
      </aside>
      <main className="flex-1 p-4 md:p-8 max-w-5xl w-full mx-auto">{children}</main>
    </div>
  );
}
