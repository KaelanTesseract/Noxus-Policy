"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (password !== confirmPassword) {
      setError("Passwörter stimmen nicht überein.");
      return;
    }

    if (password.length < 4) {
      setError("Das Passwort muss mindestens 4 Zeichen lang sein.");
      return;
    }

    setLoading(true);

    try {
      // 1. Register User
      const regRes = await fetch("/api/users/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password })
      });

      if (!regRes.ok) {
        const errData = await regRes.json();
        throw new Error(errData.detail || "Registrierung fehlgeschlagen.");
      }

      setSuccess("Konto erfolgreich erstellt! Melde dich an...");

      // 2. Automatic Login after registration
      const loginRes = await fetch("/api/users/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: email.trim(), password })
      });

      if (loginRes.ok) {
        const tokenData = await loginRes.json();
        localStorage.setItem("token", tokenData.access_token);
        setTimeout(() => {
          window.location.href = "/";
        }, 1000);
      } else {
        setTimeout(() => {
          router.push("/login");
        }, 1500);
      }
    } catch (err: any) {
      setError(err.message || "Es ist ein Fehler aufgetreten.");
    } finally {
      setLoading(false);
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
              className="relative w-24 h-24 mx-auto object-contain drop-shadow-2xl transition-transform hover:scale-105" 
            />
          </div>
          
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-zinc-100 to-zinc-400 bg-clip-text text-transparent">
              NOXUS <span className="theme-text-accent">POLICY</span>
            </h1>
            <p className="text-xs text-zinc-400 font-mono mt-1 tracking-wider uppercase">
              Kostenloses Konto erstellen
            </p>
          </div>
        </div>

        {/* Register Card */}
        <Card className="border-zinc-800/80 bg-zinc-900/40 backdrop-blur-xl shadow-2xl rounded-2xl">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-xl font-bold text-white">Registrieren</CardTitle>
            <CardDescription className="text-xs text-zinc-400">Erstelle ein Konto, um deine Versicherungen digital zu verwalten</CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-xs font-mono text-zinc-400">E-Mail-Adresse</Label>
                <Input 
                  id="email" 
                  type="email"
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
                  placeholder="Mindestens 4 Zeichen"
                  className="bg-zinc-950/60 border-zinc-800 focus:border-indigo-500" 
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-xs font-mono text-zinc-400">Passwort wiederholen</Label>
                <Input 
                  id="confirmPassword" 
                  type="password" 
                  value={confirmPassword} 
                  onChange={e => setConfirmPassword(e.target.value)} 
                  required 
                  placeholder="Passwort erneut eingeben"
                  className="bg-zinc-950/60 border-zinc-800 focus:border-indigo-500" 
                />
              </div>

              {success && (
                <div className="p-3 bg-emerald-950/50 border border-emerald-800 text-emerald-300 rounded-xl text-xs">
                  {success}
                </div>
              )}

              {error && (
                <div className="p-3 bg-red-950/50 border border-red-800/80 text-red-300 rounded-xl text-xs">
                  {error}
                </div>
              )}

              <Button type="submit" disabled={loading} className="w-full theme-bg-accent text-white theme-glow font-medium py-2.5 transition-all shadow-lg">
                {loading ? "Erstelle Konto..." : "Kostenlos registrieren →"}
              </Button>

              <div className="text-center pt-3 border-t border-zinc-800/80">
                <p className="text-xs text-zinc-400">
                  Bereits ein Konto?{" "}
                  <a href="/login" className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
                    Hier anmelden
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
