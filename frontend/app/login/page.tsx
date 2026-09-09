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
    <div className="min-h-screen flex items-center justify-center p-6">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
        <h1 className="text-xl font-bold">Sign in to CampusOps</h1>
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
        <div className="text-xs text-slate-500">Demo login: demo.student@example.com / demo1234</div>
      </form>
    </div>
  );
}
