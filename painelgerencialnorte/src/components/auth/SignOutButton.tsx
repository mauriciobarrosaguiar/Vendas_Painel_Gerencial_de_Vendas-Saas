"use client";

import { createClient } from "@/lib/supabase/client";

export function SignOutButton() {
  async function handleSignOut() {
    await createClient().auth.signOut();
    window.location.href = "/login";
  }

  return (
    <button className="rounded-md bg-primary px-4 py-2 font-semibold text-white hover:bg-[#0f5838]" type="button" onClick={handleSignOut}>
      Sair
    </button>
  );
}
