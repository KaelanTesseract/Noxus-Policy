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
import { api } from "@/lib/api";

export default function AdminSetup() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  const handleSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwörter stimmen nicht überein");
      return;
    }
    try {
      await api.post("/users/admin/initial-setup", {
        new_email: email,
        new_password: password
      });
      
      localStorage.removeItem("token");
      window.location.href = "/login";
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[85vh] py-8">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/30 via-zinc-950 to-zinc-950"></div>
      
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-3">
          <img src="/logo.png" alt="Noxus Policy Logo" className="w-20 h-20 mx-auto object-contain drop-shadow-xl" />
          <h1 className="text-2xl font-extrabold tracking-tight text-white">
            NOXUS <span className="theme-text-accent">POLICY</span>
          </h1>
        </div>

        <Card className="border-zinc-800/80 bg-zinc-900/40 backdrop-blur-xl shadow-2xl rounded-2xl ring-1 ring-indigo-500/30">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-xl font-bold text-white">Admin Ersteinrichtung</CardTitle>
            <CardDescription className="text-xs text-zinc-400">
              Bitte hinterlege eine E-Mail-Adresse und ändere das Standardpasswort.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            <form onSubmit={handleSetup} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-xs font-mono text-zinc-400">Neue E-Mail-Adresse</Label>
                <Input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)} required className="bg-zinc-950/60 border-zinc-800" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-xs font-mono text-zinc-400">Neues Passwort</Label>
                <Input id="password" type="password" value={password} onChange={e => setPassword(e.target.value)} required className="bg-zinc-950/60 border-zinc-800" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-xs font-mono text-zinc-400">Passwort bestätigen</Label>
                <Input id="confirmPassword" type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} required className="bg-zinc-950/60 border-zinc-800" />
              </div>
              {error && <p className="text-red-400 text-xs">{error}</p>}
              <Button type="submit" className="w-full theme-bg-accent text-white theme-glow font-medium py-2.5 transition-all shadow-lg">
                Speichern & Neu Anmelden →
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
