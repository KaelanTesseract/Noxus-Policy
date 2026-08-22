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

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");

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
        body: JSON.stringify({ username: email, password })
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
      localStorage.setItem("token", data.access_token);
      
      const userData = data.user || { email };
      if (typeof window !== "undefined") {
        sessionStorage.setItem("cache_user", JSON.stringify(userData));
      }
      
      if (userData.must_change_password) {
        router.push("/admin-setup");
      } else {
        router.push("/");
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[85vh] py-8">
      {/* Background glow effects */}
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/30 via-zinc-950 to-zinc-950"></div>
      
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-3">
          <div className="relative inline-block">
            <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-emerald-500 rounded-3xl blur-xl opacity-40 animate-pulse"></div>
            <img 
              src="/logo.png" 
              alt="Noxus Policy Logo" 
              className="relative w-28 h-28 mx-auto object-contain drop-shadow-2xl transition-transform hover:scale-105" 
            />
          </div>
          
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-zinc-100 to-zinc-400 bg-clip-text text-transparent">
              NOXUS <span className="theme-text-accent">POLICY</span>
            </h1>
            <p className="text-xs text-zinc-400 font-mono mt-1 tracking-wider uppercase">
              AI-Powered Insurance Management & Vision Engine
            </p>
          </div>
        </div>

        {/* Login Card */}
        <Card className="border-zinc-800/80 bg-zinc-900/40 backdrop-blur-xl shadow-2xl rounded-2xl">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-xl font-bold text-white">Willkommen zurück</CardTitle>
            <CardDescription className="text-xs text-zinc-400">Melde dich an, um deine Polizzen zu verwalten</CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            <form onSubmit={handleLogin} className="space-y-5">
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

              {error && (
                <div className="p-3 bg-red-950/50 border border-red-800/80 text-red-300 rounded-xl text-xs">
                  {error}
                </div>
              )}

              <Button type="submit" className="w-full theme-bg-accent text-white theme-glow font-medium py-2.5 transition-all shadow-lg">
                Anmelden →
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
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
