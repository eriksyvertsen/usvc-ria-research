"use client";

import { createBrowserClient } from "@supabase/ssr";
import { useState } from "react";

export default function SignInButton() {
  const [busy, setBusy] = useState(false);
  async function signIn() {
    setBusy(true);
    const sb = createBrowserClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);
    await sb.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        // hd limits Google's account picker to the AngelList workspace; the server still enforces the domain.
        queryParams: { hd: "angellist.com", prompt: "select_account" },
      },
    });
  }
  return (
    <button className="btn" style={{ width: "100%", padding: "10px 12px" }} onClick={signIn} disabled={busy}>
      {busy ? "Redirecting…" : "Sign in with Google"}
    </button>
  );
}
