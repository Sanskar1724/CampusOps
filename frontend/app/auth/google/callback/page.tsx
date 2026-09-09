"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, setToken } from "@/lib/api";

function CallbackBody() {
  const params = useSearchParams();
  const router = useRouter();
  const [msg, setMsg] = useState("Finishing Google sign-in…");

  useEffect(() => {
    (async () => {
      const code = params.get("code");
      if (!code) {
        setMsg("Google did not return a code. Please try again.");
        return;
      }
      try {
        const data = await api<{ access_token: string }>("/api/auth/google/callback", {
          method: "POST",
          body: JSON.stringify({
            code,
            redirect_uri: `${window.location.origin}/auth/google/callback`,
          }),
        });
        setToken(data.access_token);
        const me = await api<{ onboarding_status: string }>("/api/auth/me");
        router.push(me.onboarding_status === "done" ? "/dashboard" : "/onboarding");
      } catch (err: any) {
        setMsg(`Sign-in failed: ${err.message}`);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="card text-sm">{msg}</div>
    </div>
  );
}

export default function GoogleCallback() {
  return (
    <Suspense>
      <CallbackBody />
    </Suspense>
  );
}
