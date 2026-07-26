"use client"
import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token") || "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setError("Passwörter stimmen nicht überein.");
      return;
    }
    setError("");
    setMessage("");
    setLoading(true);

    try {
      const res = await fetch("/api/users/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: newPassword })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Fehler beim Zurücksetzen des Passworts.");
      }

      setMessage(data.msg || "Passwort erfolgreich geändert! Du wirst weitergeleitet...");
      setTimeout(() => {
        router.push("/login");
      }, 2000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <Card className="w-full max-w-md border-zinc-800 bg-zinc-900/40 backdrop-blur-xl shadow-2xl text-center p-6 rounded-2xl">
        <p className="text-red-400 font-medium">Ungültiger oder fehlender Zurücksetzen-Token.</p>
        <a href="/login" className="inline-block mt-4 text-xs text-indigo-400 hover:text-indigo-300">
          Zurück zur Anmeldung
        </a>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md border-zinc-800/80 bg-zinc-900/40 backdrop-blur-xl shadow-2xl rounded-2xl">
      <CardHeader className="text-center pb-2">
        <CardTitle className="text-xl font-bold text-white">Neues Passwort festlegen</CardTitle>
        <CardDescription className="text-xs text-zinc-400">
          Bitte gib dein neues Passwort ein.
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="newPassword" className="text-xs font-mono text-zinc-400">Neues Passwort</Label>
            <Input
              id="newPassword"
              type="password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              required
              className="bg-zinc-950/60 border-zinc-800"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirmPassword" className="text-xs font-mono text-zinc-400">Passwort bestätigen</Label>
            <Input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              required
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
            {loading ? "Speichert..." : "Passwort speichern →"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function ResetPasswordPage() {
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
        <Suspense fallback={<div className="text-zinc-400 text-center">Lädt...</div>}>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  );
}
