"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { clearSession, markSignedIn } from "@/lib/session";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  // Set once the password was accepted for an account that has a second factor enabled.
  const [mfaRequired, setMfaRequired] = useState(false);
  const [otp, setOtp] = useState("");
  // Which ways of signing in this instance offers (single sign-on, password).
  const [authConfig, setAuthConfig] = useState({ oidc_enabled: false, oidc_label: "", password_login_enabled: true });

  useEffect(() => {
    fetch("/api/users/auth-config")
      .then(res => (res.ok ? res.json() : null))
      .then(cfg => { if (cfg) setAuthConfig(cfg); })
      .catch(() => {});
    if (typeof window !== "undefined") {
      const problem = new URLSearchParams(window.location.search).get("error");
      if (problem === "sso_unlinked") {
        setError("Dein Konto ist noch nicht mit Single Sign-On verknüpft. Melde dich einmal mit deinem Passwort an und klicke unter Einstellungen > Single Sign-On auf „Konto jetzt verknüpfen“. Danach funktioniert die Anmeldung ohne Passwort.");
      } else if (problem === "sso") {
        setError("Die Anmeldung über Single Sign-On hat nicht geklappt. Versuche es erneut oder frage deinen Administrator.");
      }
    }
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedUser = localStorage.getItem("remembered_username");
      if (savedUser) {
        setEmail(savedUser);
        setRememberMe(true);
      }
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (rememberMe) {
        localStorage.setItem("remembered_username", email);
      } else {
        localStorage.removeItem("remembered_username");
      }

      const res = await fetch("/api/users/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: email, password, ...(mfaRequired ? { otp: otp.trim() } : {}) })
      });

      if (!res.ok) {
        let errMsg = "Login fehlgeschlagen. Bitte Zugangsdaten prüfen.";
        try {
          const text = await res.text();
          try {
            const errData = JSON.parse(text);
            if (errData.detail) {
              errMsg = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
            }
          } catch (_) {
            errMsg = `Server Fehler (${res.status}): ${text.substring(0, 100)}`;
          }
        } catch (_) {}
        throw new Error(errMsg);
      }
      const data = await res.json();
      if (data.mfa_required) {
        setMfaRequired(true);
        return;
      }
      // The token itself arrives as an httpOnly cookie (set by the proxy). Start from
      // a clean slate so cached data from a previous account in this tab can't show up.
      clearSession();
      markSignedIn();

      const userData = data.user || { email };
      if (typeof window !== "undefined") {
        sessionStorage.setItem("cache_user", JSON.stringify(userData));
      }

      if (userData.must_change_password) {
        router.push("/admin-setup");
      } else {
        // Warm the dashboard's cache before navigating so it can render instantly
        // instead of showing a blank page while it fetches the insurance list itself.
        try {
          const insRes = await fetch("/api/insurances");
          if (insRes.ok && typeof window !== "undefined") {
            sessionStorage.setItem("cache_insurances", JSON.stringify(await insRes.json()));
          }
        } catch (_) {}
        router.push("/");
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[85vh] py-8">
      {/* Background glow effects */}
      
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-3">
          <div className="relative inline-block">
            <img 
              src="/logo.png" 
              alt="Noxus Policy Logo" 
              className="relative w-28 h-28 mx-auto object-contain drop-shadow-2xl transition-transform hover:scale-105" 
            />
          </div>
          
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-zinc-50">
              Noxus Policy
            </h1>
            <p className="text-xs text-zinc-400 font-mono mt-1 tracking-wider uppercase">
              Dein Versicherungsmanager
            </p>
          </div>
        </div>

        {/* Login Card */}
        <Card className="border-zinc-800/80 bg-zinc-900/40 backdrop-blur-xl rounded-2xl">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-xl font-bold text-white">Willkommen zurück</CardTitle>
            <CardDescription className="text-xs text-zinc-400">Melde dich an, um deine Polizzen zu verwalten</CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            {authConfig.oidc_enabled && (
              <div className="space-y-4">
                <a href="/api/auth/oidc/login" className="theme-bg-accent inline-flex w-full items-center justify-center rounded-lg px-4 py-2.5 text-sm font-medium">
                  {authConfig.oidc_label || "Mit Pocket ID anmelden"}
                </a>
                {!authConfig.password_login_enabled && error && (
                  <div className="p-3 bg-red-950/50 border border-red-800/80 text-red-300 rounded-xl text-xs">{error}</div>
                )}
                {authConfig.password_login_enabled && (
                  <p className="text-center text-xs text-zinc-500">oder mit Passwort</p>
                )}
              </div>
            )}
            {authConfig.password_login_enabled && (
            <form onSubmit={handleLogin} className={`space-y-5 ${authConfig.oidc_enabled ? "mt-4" : ""}`}>
              <div className="space-y-2">
                <Label htmlFor="email" className="text-xs font-mono text-zinc-400">E-Mail oder Benutzername</Label>
                <Input 
                  id="email" 
                  value={email} 
                  onChange={e => setEmail(e.target.value)} 
                  required 
                  placeholder="name@beispiel.de"
                  className="bg-zinc-950/60 border-zinc-800 focus:border-indigo-500" 
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-xs font-mono text-zinc-400">Passwort</Label>
                <Input 
                  id="password" 
                  type="password" 
                  value={password} 
                  onChange={e => setPassword(e.target.value)} 
                  required 
                  placeholder="••••••••"
                  className="bg-zinc-950/60 border-zinc-800 focus:border-indigo-500" 
                />
              </div>

              <div className="flex items-center justify-between pt-1">
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="rememberMe"
                    checked={rememberMe}
                    onChange={e => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-zinc-700 bg-zinc-950 text-indigo-600 focus:ring-indigo-500 accent-indigo-600 cursor-pointer"
                  />
                  <Label htmlFor="rememberMe" className="text-xs text-zinc-300 cursor-pointer select-none">
                    Benutzernamen merken
                  </Label>
                </div>
                <a href="/forgot-password" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors font-medium">
                  Passwort vergessen?
                </a>
              </div>

              {mfaRequired && (
                <div className="space-y-2">
                  <Label htmlFor="otp" className="text-xs font-mono text-zinc-400">Bestätigungscode (2-Faktor)</Label>
                  <Input
                    id="otp"
                    value={otp}
                    onChange={e => setOtp(e.target.value)}
                    required
                    autoFocus
                    autoComplete="one-time-code"
                    inputMode="text"
                    placeholder="6-stelliger Code oder Wiederherstellungscode"
                    className="bg-zinc-950/60 border-zinc-800 focus:border-indigo-500 font-mono tracking-wider"
                  />
                  <p className="text-[11px] text-zinc-500">
                    Öffne deine Authenticator-App und gib den aktuellen Code ein. Ohne Zugriff auf die App kannst du einen Wiederherstellungscode verwenden.
                  </p>
                </div>
              )}

              {error && (
                <div className="p-3 bg-red-950/50 border border-red-800/80 text-red-300 rounded-xl text-xs">
                  {error}
                </div>
              )}

              <Button type="submit" className="w-full theme-bg-accent text-white theme-glow font-medium py-2.5 transition-all shadow-lg">
                {mfaRequired ? "Bestätigen →" : "Anmelden →"}
              </Button>

              <div className="text-center pt-3 border-t border-zinc-800/80">
                <p className="text-xs text-zinc-400">
                  Noch kein Konto?{" "}
                  <a href="/register" className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
                    Hier kostenlos registrieren
                  </a>
                </p>
              </div>
            </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
