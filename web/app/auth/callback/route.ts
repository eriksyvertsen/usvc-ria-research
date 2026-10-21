import { NextResponse, type NextRequest } from "next/server";
import { isAllowed, supabaseAuth } from "@/lib/auth";

export async function GET(req: NextRequest) {
  const code = req.nextUrl.searchParams.get("code");
  const origin = req.nextUrl.origin;
  if (!code) return NextResponse.redirect(`${origin}/login?error=auth`);

  const sb = await supabaseAuth();
  const { data, error } = await sb.auth.exchangeCodeForSession(code);
  if (error) return NextResponse.redirect(`${origin}/login?error=auth`);
  if (!isAllowed(data.user?.email)) {
    await sb.auth.signOut();
    return NextResponse.redirect(`${origin}/login?error=domain`);
  }
  return NextResponse.redirect(`${origin}/`);
}
