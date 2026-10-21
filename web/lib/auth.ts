import "server-only";
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export const ALLOWED_DOMAIN = "angellist.com";

export function isAllowed(email: string | null | undefined): boolean {
  return !!email && email.toLowerCase().endsWith(`@${ALLOWED_DOMAIN}`);
}

export async function supabaseAuth() {
  const store = await cookies();
  return createServerClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, {
    cookies: {
      getAll: () => store.getAll(),
      setAll: (list) => {
        try {
          list.forEach(({ name, value, options }) => store.set(name, value, options));
        } catch {
          // Server Components can't set cookies; middleware refreshes the session.
        }
      },
    },
  });
}

/** Server-side gate for every page that reads lead data (middleware is the first line). */
export async function requireUser() {
  const sb = await supabaseAuth();
  const { data } = await sb.auth.getUser();
  if (!data.user) redirect("/login");
  if (!isAllowed(data.user.email)) redirect("/login?error=domain");
  return data.user;
}
