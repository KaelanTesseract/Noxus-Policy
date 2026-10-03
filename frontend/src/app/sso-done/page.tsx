"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { clearSession, markSignedIn } from "@/lib/session";

// Landing page after a successful single sign-on. By now the proxy has turned the
// session token into the httpOnly cookie; all that is left for the browser is to
// note that someone is signed in (and to drop cached data of any earlier account).
export default function SsoDone() {
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/users/me");
        if (!res.ok) throw new Error("no session");
        const user = await res.json();
        if (cancelled) return;
        clearSession();
        markSignedIn();
        sessionStorage.setItem("cache_user", JSON.stringify(user));
        router.replace(user.must_change_password ? "/admin-setup" : "/");
      } catch (_) {
        if (!cancelled) window.location.href = "/login?error=sso";
      }
    })();
    return () => { cancelled = true; };
  }, [router]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <p className="text-sm text-zinc-400" role="status">Anmeldung wird abgeschlossen …</p>
    </div>
  );
}
