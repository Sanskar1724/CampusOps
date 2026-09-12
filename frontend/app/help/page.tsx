"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

export default function Help() {
  const [md, setMd] = useState("Loading guide…");

  useEffect(() => {
    api<{ markdown: string }>("/api/system/help")
      .then((d) => setMd(d.markdown))
      .catch((e) => setMd(`Could not load the guide: ${e.message}`));
  }, []);

  return (
    <Shell>
      <h1 className="text-2xl font-bold mb-4">❓ Help & User Guide</h1>
      <div className="card">
        <div className="text-sm whitespace-pre-wrap leading-relaxed">{md}</div>
      </div>
    </Shell>
  );
}
