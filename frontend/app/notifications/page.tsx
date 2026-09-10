"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

export default function Notifications() {
  const [items, setItems] = useState<any[]>([]);

  useEffect(() => {
    api<any[]>("/api/notifications/").then(setItems).catch(() => {});
  }, []);

  return (
    <Shell>
      <h1 className="text-2xl font-bold mb-4">Notifications</h1>
      <div className="card">
        {items.length === 0 && <div className="text-sm text-slate-500">No notifications yet.</div>}
        {items.map((n) => (
          <div key={n.id} className="py-2 border-t border-slate-100 first:border-0 text-sm">
            <div className="font-medium">
              {n.title} <span className="text-xs text-slate-500">· {n.kind} · {n.status}</span>
            </div>
            <div className="text-slate-600 whitespace-pre-wrap">{n.body}</div>
          </div>
        ))}
      </div>
    </Shell>
  );
}
