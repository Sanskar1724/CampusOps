"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, setToken } from "@/lib/api";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const data = await api<{ access_token: string }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ college_email: email, password }),
      });
      setToken(data.access_token);
      const me = await api<{ onboarding_status: string }>("/api/auth/me");
      router.push(me.onboarding_status === "done" ? "/dashboard" : "/onboarding");
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-br from-indigo-50 via-white to-slate-100">
      <div className="w-full max-w-sm space-y-3">
      <form onSubmit={submit} className="card w-full space-y-4">
        <Link href="/" className="text-sm text-slate-500 hover:text-indigo-600">← Back to home</Link>
        <h1 className="text-xl font-bold">🎓 Sign in to CampusOps</h1>
        <div className="text-xs bg-indigo-50 border border-indigo-200 text-indigo-700 rounded-lg p-2.5">
          Just exploring? One click fills a sample account — no setup needed.
        </div>
        <button
          type="button"
          className="btn w-full !bg-emerald-600 hover:!bg-emerald-700"
          onClick={() => {
            setEmail("demo.student@example.com");
            setPassword("demo1234");
            setError("");
          }}
        >
          Fill sample login
        </button>
        {error && <div className="text-sm text-red-600">{error}</div>}
        <div>
          <label className="label">College email</label>
          <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label className="label">Password</label>
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button className="btn w-full" type="submit">Sign in</button>
        <div className="text-sm text-slate-600">
          New here? <Link href="/register" className="text-indigo-600">Create an account</Link>
        </div>
        <div className="text-xs text-slate-500">Sample login: demo.student@example.com / demo1234</div>
      </form>
      <button
        className="btn-ghost w-full bg-white"
        onClick={async () => {
          setError("");
          try {
            const redirect = `${window.location.origin}/auth/google/callback`;
            const data = await api<{ auth_url: string }>(
              `/api/auth/google/url?redirect_uri=${encodeURIComponent(redirect)}`);
            window.location.href = data.auth_url;
          } catch (err: any) {
            setError(err.message);
          }
        }}
      >
        <span className="mr-2 font-bold text-indigo-600">G</span> Continue with Google
      </button>
      </div>
    </div>
  );
}
