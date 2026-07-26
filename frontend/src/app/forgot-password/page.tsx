"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      const res = await fetch("/api/users/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email })
      });

      const data = await res.json();
      setMessage(data.msg || "Falls diese E-Mail-Adresse registriert ist, wurde eine E-Mail gesendet.");
    } catch (err: any) {
      setError("Es ist ein Fehler aufgetreten. Bitte versuche es erneut.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[85vh] py-8">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/30 via-zinc-950 to-zinc-950"></div>
      
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-3">
          <img src="/logo.png" alt="Noxus Policy Logo" className="w-20 h-20 mx-auto object-contain drop-shadow-xl" />
          <h1 className="text-2xl font-extrabold tracking-tight text-white">
            NOXUS <span className="theme-text-accent">POLICY</span>
          </h1>
        </div>

        <Card className="border-zinc-800/80 bg-zinc-900/40 backdrop-blur-xl shadow-2xl rounded-2xl">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-xl font-bold text-white">Passwort vergessen</CardTitle>
            <CardDescription className="text-xs text-zinc-400">
              Gib deine E-Mail-Adresse ein. Wir senden dir einen Link zum Zurücksetzen.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-xs font-mono text-zinc-400">E-Mail-Adresse</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  placeholder="name@beispiel.de"
                  className="bg-zinc-950/60 border-zinc-800"
                />
              </div>

              {message && (
                <div className="p-3 bg-emerald-950/50 border border-emerald-800 text-emerald-300 rounded-xl text-xs">
                  {message}
                </div>
              )}

              {error && <p className="text-red-400 text-xs">{error}</p>}

              <Button
                type="submit"
                disabled={loading}
                className="w-full theme-bg-accent text-white theme-glow font-medium py-2.5 transition-all shadow-lg"
              >
                {loading ? "Sende E-Mail..." : "Link anfordern →"}
              </Button>

              <div className="text-center pt-2">
                <a href="/login" className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors">
                  ← Zurück zur Anmeldung
                </a>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
