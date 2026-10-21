import SignInButton from "./signin-button";

export const dynamic = "force-dynamic";

export default async function Login({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  return (
    <main className="wrap" style={{ maxWidth: 420, paddingTop: 96 }}>
      <section className="panel" style={{ padding: 28 }}>
        <h1>RIA Venture Leads</h1>
        <p className="sub">Sign in with your AngelList Google account.</p>
        {error === "domain" && (
          <p style={{ color: "var(--tier-b)" }}>Only @angellist.com accounts can access this dashboard.</p>
        )}
        {error === "auth" && <p style={{ color: "var(--tier-b)" }}>Sign-in failed. Please try again.</p>}
        <SignInButton />
      </section>
    </main>
  );
}
