"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

export default function Settings() {
  const [integrations, setIntegrations] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [code, setCode] = useState("");
  const [sys, setSys] = useState<any>(null);

  async function refresh() {
    setIntegrations(await api<any[]>("/api/integrations/"));
  }
  useEffect(() => {
    refresh().catch(() => {});
    api<any>("/api/system/status").then(setSys).catch(() => {});
  }, []);

  const gmail = integrations.find((i) => i.provider === "gmail");

  return (
    <Shell>
      <h1 className="text-2xl font-bold mb-4">⚙️ Settings</h1>
      <div className="card max-w-lg mb-4">
        <div className="font-semibold mb-2">ðŸ”Œ Backend connections</div>
        {!sys && <div className="text-sm text-slate-500">Checkingâ€¦</div>}
        {sys && (
          <div className="space-y-1.5">
            <div className={`text-sm font-medium ${sys.all_ok ? "text-emerald-700" : "text-amber-700"}`}>
              {sys.all_ok ? "âœ“ Everything connected" : "âš  Something needs attention"}
            </div>
            {sys.checks.map((c: any) => (
              <div key={c.name} className="text-sm flex items-start gap-2">
                <span>{c.ok ? "ðŸŸ¢" : "ðŸ”´"}</span>
                <span>
                  <span className="font-mono text-xs">{c.name}</span>
                  {c.detail && <span className="text-slate-500"> Â· {c.detail}</span>}
                  {!c.ok && c.hint && <span className="block text-xs text-slate-600">{c.hint}</span>}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="card max-w-lg space-y-3">
        <div className="font-semibold">College email (Gmail, read-only OAuth)</div>
        <div className="text-sm text-slate-600">
          Status: {gmail ? `${gmail.status} ${gmail.account}` : "not connected"}. CampusOps
          never asks for your email password.
        </div>
        <div className="flex gap-2">
          <button
            className="btn"
            onClick={async () => {
              setMsg("");
              try {
                const data = await api<{ auth_url: string }>("/api/integrations/gmail/auth-url");
                window.open(data.auth_url, "_blank");
                setMsg("Complete Google consent, then paste the code below.");
              } catch (e: any) {
                setMsg(e.message);
              }
            }}
          >
            Connect Gmail
          </button>
          {gmail?.status === "connected" && (
            <button
              className="btn-ghost"
              onClick={async () => {
                await api("/api/integrations/gmail", { method: "DELETE" });
                refresh();
              }}
            >
              Disconnect
            </button>
          )}
          <button className="btn-ghost" onClick={refresh}>
            Refresh status
          </button>
        </div>
        <form
          className="flex gap-2"
          onSubmit={async (e) => {
            e.preventDefault();
            setMsg("");
            try {
              await api("/api/integrations/gmail/callback", {
                method: "POST",
                body: JSON.stringify({ code }),
              });
              setCode("");
              refresh();
              setMsg("Gmail connected.");
            } catch (err: any) {
              setMsg(err.message);
            }
          }}
        >
          <input
            className="input"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Paste Google code here"
          />
          <button className="btn-ghost" type="submit">Finish</button>
        </form>
        {msg && <div className="text-sm text-slate-600">{msg}</div>}
        <div className="text-xs text-slate-500">
          Backend: {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
        </div>
      </div>
    </Shell>
  );
}
