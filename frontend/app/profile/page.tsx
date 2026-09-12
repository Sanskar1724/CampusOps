"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

export default function Profile() {
  const [me, setMe] = useState<any>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api<any>("/api/auth/me").then((m) => {
      setMe(m);
      setForm(m);
    });
  }, []);

  return (
    <Shell>
      <h1 className="text-2xl font-bold mb-4">👤 Student Profile</h1>
      {me && (
        <div className="flex items-center gap-3 mb-4">
          <div className="w-14 h-14 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 text-white text-xl font-bold flex items-center justify-center">
            {(me.full_name || me.college_email || "?").trim().charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="font-semibold">{me.full_name || "Your profile"}</div>
            <div className="text-xs text-slate-500">{me.college_email} · PRN {me.prn}</div>
          </div>
        </div>
      )}
      {me && (
        <form
          className="card space-y-3 max-w-lg"
          onSubmit={async (e) => {
            e.preventDefault();
            setMsg("");
            try {
              const updated = await api<any>("/api/student/profile", {
                method: "PATCH",
                body: JSON.stringify({
                  full_name: form.full_name,
                  department: form.department,
                  division: form.division,
                  batch: form.batch,
                  roll_number: form.roll_number,
                  semester: form.semester,
                }),
              });
              setMe(updated);
              setMsg("Profile saved.");
            } catch (err: any) {
              setMsg(err.message);
            }
          }}
        >
          {[
            ["full_name", "Full name"],
            ["prn", "PRN"],
            ["college_email", "College email"],
            ["department", "Department"],
            ["division", "Division"],
            ["batch", "Batch"],
            ["roll_number", "Roll number"],
            ["semester", "Semester"],
          ].map(([key, label]) => (
            <div key={key}>
              <label className="label">{label}</label>
              <input
                className="input"
                value={form[key] || ""}
                disabled={["prn", "college_email"].includes(key)}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              />
            </div>
          ))}
          <button className="btn" type="submit">Save</button>
          {msg && <div className="text-sm text-slate-600">{msg}</div>}
          <div className="text-xs text-slate-500">
            PRN and email identify your account and can't be changed here. Your data is
            visible only to you.
          </div>
        </form>
      )}
    </Shell>
  );
}
