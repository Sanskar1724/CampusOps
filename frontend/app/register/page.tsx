"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, setToken } from "@/lib/api";

const FIELDS = [
  ["full_name", "Full name"],
  ["prn", "PRN"],
  ["department", "Department"],
  ["division", "Division"],
  ["batch", "Batch"],
  ["roll_number", "Roll number"],
  ["semester", "Semester"],
  ["college_email", "College email"],
] as const;

export default function Register() {
  const router = useRouter();
  const [form, setForm] = useState<Record<string, string>>({ password: "" });
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const data = await api<{ access_token: string }>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(form),
      });
      setToken(data.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form onSubmit={submit} className="card w-full max-w-md space-y-3">
        <h1 className="text-xl font-bold">Create your CampusOps profile</h1>
        {error && <div className="text-sm text-red-600">{error}</div>}
        <div className="grid grid-cols-2 gap-3">
          {FIELDS.map(([key, label]) => (
            <div key={key} className={key === "full_name" || key === "college_email" ? "col-span-2" : ""}>
              <label className="label">{label}</label>
              <input
                className="input"
                value={form[key] || ""}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                required={["prn", "college_email"].includes(key)}
              />
            </div>
          ))}
        </div>
        <div>
          <label className="label">Password (min 6 chars)</label>
          <input
            className="input" type="password" minLength={6}
            value={form.password || ""}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
        </div>
        <button className="btn w-full" type="submit">Create account</button>
        <div className="text-sm text-slate-600">
          Have an account? <Link href="/login" className="text-indigo-600">Sign in</Link>
        </div>
      </form>
    </div>
  );
}
