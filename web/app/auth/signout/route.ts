import { NextResponse, type NextRequest } from "next/server";
import { supabaseAuth } from "@/lib/auth";

export async function POST(req: NextRequest) {
  const sb = await supabaseAuth();
  await sb.auth.signOut();
  return NextResponse.redirect(`${req.nextUrl.origin}/login`, { status: 303 });
}
