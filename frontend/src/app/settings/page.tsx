"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useTheme, THEMES, STYLES } from "@/components/ThemeProvider";
import { Navbar } from "@/components/Navbar";

interface User {
  id: number;
  email: string;
  is_admin: boolean;
  must_change_password: boolean;
}

interface StoredBackup {
  filename: string;
  size_mb: number;
  size_bytes: number;
  created_at: string;
  type: string;
}

export default function SettingsPage() {
  const router = useRouter();
  const { theme, setTheme, styleTheme, setStyleTheme } = useTheme();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [activeTab, setActiveTab] = useState<"general" | "system">("general");
  
  // Profile form
  const [email, setEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [profileMsg, setProfileMsg] = useState("");
  const [profileErr, setProfileErr] = useState("");
  const [profileLoading, setProfileLoading] = useState(false);

  // Admin SMTP form state
  const [appUrl, setAppUrl] = useState("http://192.168.1.251:3000");
  const [smtpServer, setSmtpServer] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpUsername, setSmtpUsername] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [smtpFrom, setSmtpFrom] = useState("no-reply@noxus-policy.local");
  const [smtpUseTls, setSmtpUseTls] = useState(true);
  const [showSmtpPassword, setShowSmtpPassword] = useState(false);
  const [smtpMsg, setSmtpMsg] = useState("");
  const [smtpErr, setSmtpErr] = useState("");
  const [smtpSaving, setSmtpSaving] = useState(false);
  const [smtpTesting, setSmtpTesting] = useState(false);

  // Manual System Backup export state
  const [backupExportPassword, setBackupExportPassword] = useState("");
  const [backupExportConfirm, setBackupExportConfirm] = useState("");
  const [backupExportMsg, setBackupExportMsg] = useState("");
  const [backupExportErr, setBackupExportErr] = useState("");
  const [backupExporting, setBackupExporting] = useState(false);

  // Manual System Backup import state
  const [backupImportFile, setBackupImportFile] = useState<File | null>(null);
  const [backupImportPassword, setBackupImportPassword] = useState("");
  const [backupImportMsg, setBackupImportMsg] = useState("");
  const [backupImportErr, setBackupImportErr] = useState("");
  const [backupImporting, setBackupImporting] = useState(false);

  // Automated Backup Settings state
  const [autoBackupEnabled, setAutoBackupEnabled] = useState(false);
  const [autoBackupInterval, setAutoBackupInterval] = useState("daily");
  const [autoBackupTime, setAutoBackupTime] = useState("03:00");
  const [autoBackupPassword, setAutoBackupPassword] = useState("");
  const [autoBackupRetentionDays, setAutoBackupRetentionDays] = useState("14");
  const [autoBackupRetentionCount, setAutoBackupRetentionCount] = useState("10");
  const [autoBackupLastRun, setAutoBackupLastRun] = useState("");
  const [autoBackupMsg, setAutoBackupMsg] = useState("");
  const [autoBackupErr, setAutoBackupErr] = useState("");
  const [autoBackupSaving, setAutoBackupSaving] = useState(false);
  const [autoBackupRunning, setAutoBackupRunning] = useState(false);

  // Stored Backups List
  const [storedBackups, setStoredBackups] = useState<StoredBackup[]>([]);
  const [loadingStoredBackups, setLoadingStoredBackups] = useState(false);
  const [restorePasswordInput, setRestorePasswordInput] = useState<{ [filename: string]: string }>({});
  const [restoringFilename, setRestoringFilename] = useState<string | null>(null);
  const [deletingFilename, setDeletingFilename] = useState<string | null>(null);

  // Single User Export / Import State
  const [exportingUserId, setExportingUserId] = useState<number | null>(null);
  const [showUserImportBox, setShowUserImportBox] = useState(false);
  const [userImportFile, setUserImportFile] = useState<File | null>(null);
  const [userImportPassword, setUserImportPassword] = useState("");
  const [userImporting, setUserImporting] = useState(false);
  const [userImportMsg, setUserImportMsg] = useState("");
  const [userImportErr, setUserImportErr] = useState("");

  // AI OCR Config State
  const [useAiOcr, setUseAiOcr] = useState(true);
  const [aiConfigMsg, setAiConfigMsg] = useState("");
  const [aiConfigErr, setAiConfigErr] = useState("");
  const [aiConfigSaving, setAiConfigSaving] = useState(false);

  // Admin actions notification
  const [adminMsg, setAdminMsg] = useState("");
  const [adminErr, setAdminErr] = useState("");
  const [sendingEmailId, setSendingEmailId] = useState<number | null>(null);
  const [deletingUserId, setDeletingUserId] = useState<number | null>(null);

  useEffect(() => {
    loadUserData();
  }, []);

  const loadUserData = async () => {
    try {
      const user = await api.get("/users/me");
      setCurrentUser(user);
      setEmail(user.email);

      if (user.is_admin) {
        const usersList = await api.get("/users/all");
        setAllUsers(usersList);

        // Load AI Config
        try {
          const aiConfig = await api.get("/documents/ai-config");
          setUseAiOcr(aiConfig.use_ai);
        } catch (aiErr) {
          console.error("Error loading AI config:", aiErr);
        }

        // Load SMTP Config
        try {
          const smtpConfig = await api.get("/users/smtp-config");
          setAppUrl(smtpConfig.app_url || "http://192.168.1.251:3000");
          setSmtpServer(smtpConfig.smtp_server || "");
          setSmtpPort(smtpConfig.smtp_port || "587");
          setSmtpUsername(smtpConfig.smtp_username || "");
          setSmtpPassword(smtpConfig.smtp_password || "");
          setSmtpFrom(smtpConfig.smtp_from || "no-reply@noxus-policy.local");
          setSmtpUseTls(!!smtpConfig.smtp_use_tls);
        } catch (smtpErr) {
          console.error("Error loading SMTP config:", smtpErr);
        }

        // Load Auto Backup Config
        try {
          const autoConfig = await api.get("/backup/config");
          setAutoBackupEnabled(autoConfig.enabled);
          setAutoBackupInterval(autoConfig.interval || "daily");
          setAutoBackupTime(autoConfig.time || "03:00");
          setAutoBackupPassword(autoConfig.password || "");
          setAutoBackupRetentionDays(String(autoConfig.retention_days ?? 14));
          setAutoBackupRetentionCount(String(autoConfig.retention_count ?? 10));
          setAutoBackupLastRun(autoConfig.last_run || "");
        } catch (autoErr) {
          console.error("Error loading auto backup config:", autoErr);
        }

        // Load Stored Backups
        loadStoredBackupsList();
      }
    } catch (err: any) {
      console.error(err);
      localStorage.removeItem("token");
      router.push("/login");
    }
  };

  const loadStoredBackupsList = async () => {
    setLoadingStoredBackups(true);
    try {
      const list = await api.get("/backup/list");
      setStoredBackups(list);
    } catch (err: any) {
      console.error("Error loading stored backups list:", err);
    } finally {
      setLoadingStoredBackups(false);
    }
  };

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileMsg("");
    setProfileErr("");

    if (newPassword && newPassword !== confirmPassword) {
      setProfileErr("Passwörter stimmen nicht überein.");
      return;
    }

    setProfileLoading(true);
    try {
      const updated = await api.put("/users/profile", {
        email: email !== currentUser?.email ? email : undefined,
        new_password: newPassword ? newPassword : undefined,
      });

      setCurrentUser(updated);
      setEmail(updated.email);
      setNewPassword("");
      setConfirmPassword("");
      setProfileMsg("Profil erfolgreich aktualisiert!");
    } catch (err: any) {
      setProfileErr(err.message || "Fehler beim Aktualisieren des Profils.");
    } finally {
      setProfileLoading(false);
    }
  };

  const handleSaveAiConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setAiConfigMsg("");
    setAiConfigErr("");
    setAiConfigSaving(true);

    try {
      const res = await api.post("/documents/ai-config", { use_ai: useAiOcr });
      setAiConfigMsg(res.msg || "KI-Einstellungen erfolgreich gespeichert!");
    } catch (err: any) {
      setAiConfigErr(err.message || "Fehler beim Speichern der KI-Einstellungen.");
    } finally {
      setAiConfigSaving(false);
    }
  };

  const handleSmtpSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSmtpMsg("");
    setSmtpErr("");
    setSmtpSaving(true);

    try {
      const res = await api.post("/users/smtp-config", {
        app_url: appUrl,
        smtp_server: smtpServer,
        smtp_port: smtpPort,
        smtp_username: smtpUsername,
        smtp_password: smtpPassword,
        smtp_from: smtpFrom,
        smtp_use_tls: smtpUseTls
      });
      setSmtpMsg(res.msg || "SMTP-Einstellungen erfolgreich gespeichert!");
    } catch (err: any) {
      setSmtpErr(err.message || "Fehler beim Speichern der SMTP-Einstellungen.");
    } finally {
      setSmtpSaving(false);
    }
  };

  const handleSmtpTest = async () => {
    setSmtpMsg("");
    setSmtpErr("");
    setSmtpTesting(true);

    try {
      await api.post("/users/smtp-config", {
        app_url: appUrl,
        smtp_server: smtpServer,
        smtp_port: smtpPort,
        smtp_username: smtpUsername,
        smtp_password: smtpPassword,
        smtp_from: smtpFrom,
        smtp_use_tls: smtpUseTls
      });

      const res = await api.post("/users/smtp-test", {
        target_email: currentUser?.email
      });
      setSmtpMsg(res.msg || `Test-E-Mail erfolgreich an ${currentUser?.email} versendet!`);
    } catch (err: any) {
      setSmtpErr(err.message || "Fehler beim Versenden der Test-E-Mail.");
    } finally {
      setSmtpTesting(false);
    }
  };

  const handleSaveAutoBackupConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setAutoBackupMsg("");
    setAutoBackupErr("");
    setAutoBackupSaving(true);

    try {
      const res = await api.post("/backup/config", {
        enabled: autoBackupEnabled,
        interval: autoBackupInterval,
        time: autoBackupTime,
        password: autoBackupPassword,
        retention_days: parseInt(autoBackupRetentionDays) || 0,
        retention_count: parseInt(autoBackupRetentionCount) || 0
      });

      setAutoBackupMsg(res.msg || "Automatische Backup-Einstellungen erfolgreich gespeichert!");
      loadStoredBackupsList();
    } catch (err: any) {
      setAutoBackupErr(err.message || "Fehler beim Speichern der Backup-Einstellungen.");
    } finally {
      setAutoBackupSaving(false);
    }
  };

  const handleRunBackupNow = async () => {
    setAutoBackupMsg("");
    setAutoBackupErr("");
    setAutoBackupRunning(true);

    try {
      const res = await api.post("/backup/run-now", {});
      setAutoBackupMsg(res.msg || "Backup wurde erfolgreich sofort auf dem Server erstellt!");
      loadStoredBackupsList();
    } catch (err: any) {
      setAutoBackupErr(err.message || "Fehler beim Erstellen des Backups.");
    } finally {
      setAutoBackupRunning(false);
    }
  };

  const handleExportBackup = async (e: React.FormEvent) => {
    e.preventDefault();
    setBackupExportMsg("");
    setBackupExportErr("");

    if (!backupExportPassword || backupExportPassword.length < 4) {
      setBackupExportErr("Bitte gib ein mindestens 4-stelliges Passwort ein.");
      return;
    }
    if (backupExportPassword !== backupExportConfirm) {
      setBackupExportErr("Passwörter stimmen nicht überein.");
      return;
    }

    setBackupExporting(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("/api/backup/export", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ password: backupExportPassword })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Fehler beim Erstellen des Backups.");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `noxus_policy_backup_${new Date().toISOString().slice(0, 10)}.noxusbackup`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setBackupExportMsg("Verschlüsseltes System-Backup erfolgreich erstellt & heruntergeladen!");
      setBackupExportPassword("");
      setBackupExportConfirm("");
    } catch (err: any) {
      setBackupExportErr(err.message || "Fehler beim Exportieren des Backups.");
    } finally {
      setBackupExporting(false);
    }
  };

  const handleImportBackup = async (e: React.FormEvent) => {
    e.preventDefault();
    setBackupImportMsg("");
    setBackupImportErr("");

    if (!backupImportFile) {
      setBackupImportErr("Bitte wähle eine .noxusbackup Datei aus.");
      return;
    }
    if (!backupImportPassword) {
      setBackupImportErr("Bitte gib das Passwort zur Entschlüsselung ein.");
      return;
    }

    if (!window.confirm("⚠️ ACHTUNG: Das Einspielen des Backups überschreibt den aktuellen Datenbestand auf diesem Server! Möchtest du wirklich fortfahren?")) {
      return;
    }

    setBackupImporting(true);
    try {
      const token = localStorage.getItem("token");
      const fd = new FormData();
      fd.append("file", backupImportFile);
      fd.append("password", backupImportPassword);

      const res = await fetch("/api/backup/import", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: fd
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Fehler beim Importieren des Backups.");
      }

      setBackupImportMsg(data.msg || "System-Backup erfolgreich wiederhergestellt!");
      setBackupImportPassword("");
      setBackupImportFile(null);
      setTimeout(() => {
        loadUserData();
      }, 1500);
    } catch (err: any) {
      setBackupImportErr(err.message || "Fehler beim Wiederherstellen des Backups.");
    } finally {
      setBackupImporting(false);
    }
  };

  // Export a single user's data package (.noxususer)
  const handleExportUser = async (userId: number, targetEmail: string) => {
    const pwd = window.prompt(`Gib ein Passwort für die Verschlüsselung der Daten von "${targetEmail}" ein (mindestens 4 Zeichen):`);
    if (!pwd || pwd.trim().length < 4) {
      if (pwd !== null) alert("Das Passwort muss mindestens 4 Zeichen lang sein.");
      return;
    }

    setExportingUserId(userId);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`/api/backup/export-user/${userId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ password: pwd.trim() })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Fehler beim Exportieren des Benutzers.");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const cleanEmail = targetEmail.replace("@", "_at_").replace(".", "_");
      a.download = `noxus_user_backup_${cleanEmail}_${new Date().toISOString().slice(0, 10)}.noxususer`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      alert(`Benutzer-Backup für ${targetEmail} wurde erfolgreich heruntergeladen!`);
    } catch (err: any) {
      alert(err.message || "Fehler beim Exportieren des Benutzers.");
    } finally {
      setExportingUserId(null);
    }
  };

  // Import a single user's data package (.noxususer)
  const handleImportUserSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setUserImportMsg("");
    setUserImportErr("");

    if (!userImportFile) {
      setUserImportErr("Bitte wähle eine .noxususer Datei aus.");
      return;
    }
    if (!userImportPassword) {
      setUserImportErr("Bitte gib das Entschlüsselungs-Passwort an.");
      return;
    }

    setUserImporting(true);
    try {
      const token = localStorage.getItem("token");
      const fd = new FormData();
      fd.append("file", userImportFile);
      fd.append("password", userImportPassword);

      const res = await fetch("/api/backup/import-user", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: fd
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Fehler beim Importieren des Benutzers.");
      }

      setUserImportMsg(data.msg || "Benutzer erfolgreich importiert!");
      setUserImportPassword("");
      setUserImportFile(null);
      loadUserData();
    } catch (err: any) {
      setUserImportErr(err.message || "Fehler beim Importieren des Benutzers.");
    } finally {
      setUserImporting(false);
    }
  };

  const handleDownloadStoredBackup = async (filename: string) => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`/api/backup/download/${filename}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error("Fehler beim Herunterladen.");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert("Fehler beim Herunterladen des Backups.");
    }
  };

  const handleRestoreStoredBackup = async (filename: string) => {
    const pwd = restorePasswordInput[filename] || autoBackupPassword;
    if (!pwd) {
      alert("Bitte gib das Entschlüsselungs-Passwort für dieses Backup ein.");
      return;
    }

    if (!window.confirm(`⚠️ ACHTUNG: Möchtest du das Backup "${filename}" wirklich einspielen? Der aktuelle Datenbestand auf diesem Server wird überschrieben!`)) {
      return;
    }

    setRestoringFilename(filename);
    try {
      const res = await api.post(`/backup/restore-stored/${filename}`, { password: pwd });
      alert(res.msg || "Backup wurde erfolgreich wiederhergestellt!");
      setTimeout(() => {
        loadUserData();
      }, 1500);
    } catch (err: any) {
      alert(err.message || "Fehler beim Wiederherstellen des Backups.");
    } finally {
      setRestoringFilename(null);
    }
  };

  const handleDeleteStoredBackup = async (filename: string) => {
    if (!window.confirm(`Möchtest du das Server-Backup "${filename}" wirklich löschen?`)) {
      return;
    }

    setDeletingFilename(filename);
    try {
      const res = await api.delete(`/backup/delete-stored/${filename}`);
      setStoredBackups(prev => prev.filter(b => b.filename !== filename));
    } catch (err: any) {
      alert(err.message || "Fehler beim Löschen des Backups.");
    } finally {
      setDeletingFilename(null);
    }
  };

  const handleSendResetEmail = async (userEmail: string, userId: number) => {
    setAdminMsg("");
    setAdminErr("");
    setSendingEmailId(userId);

    try {
      const res = await api.post(`/users/admin/send-reset-email?email=${encodeURIComponent(userEmail)}`, {});
      setAdminMsg(res.msg || `Passwort-Zurücksetzen-E-Mail wurde an ${userEmail} gesendet.`);
    } catch (err: any) {
      setAdminErr(err.message || "Fehler beim Versenden der E-Mail.");
    } finally {
      setSendingEmailId(null);
    }
  };

  const handleDeleteUser = async (user: User) => {
    if (!window.confirm(`Möchtest du den Benutzer "${user.email}" wirklich unwiderruflich löschen? Alle zugehörigen Versicherungsdaten werden entfernt.`)) {
      return;
    }

    setAdminMsg("");
    setAdminErr("");
    setDeletingUserId(user.id);

    try {
      const res = await api.delete(`/users/${user.id}`);
      setAdminMsg(res.msg || `Benutzer ${user.email} wurde erfolgreich gelöscht.`);
      setAllUsers(prev => prev.filter(u => u.id !== user.id));
    } catch (err: any) {
      setAdminErr(err.message || "Fehler beim Löschen des Benutzers.");
    } finally {
      setDeletingUserId(null);
    }
  };

  if (!currentUser) {
    return null;
  }

  return (
    <div className="space-y-6 flex-1">
      <Navbar userEmail={currentUser.email} />

      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center border-b border-zinc-800/80 pb-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white">Einstellungen</h1>
            <p className="text-sm text-zinc-400 mt-1">
              {currentUser.is_admin 
                ? "Verwalte dein Konto, Farbschema sowie administrative Systemeinstellungen" 
                : "Verwalte dein Konto und Farbschema"}
            </p>
          </div>
          <Button variant="outline" onClick={() => router.push("/")} className="border-zinc-800 bg-zinc-900/50 hover:bg-zinc-800 text-zinc-300">
            ← Zurück zur Übersicht
          </Button>
        </div>

        {/* Admin Navigation Tabs */}
        {currentUser.is_admin && (
          <div className="flex border-b border-zinc-800/80 space-x-6">
            <button
              onClick={() => setActiveTab("general")}
              className={`pb-3 px-1 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
                activeTab === "general"
                  ? "theme-text-accent border-indigo-500"
                  : "text-zinc-400 border-transparent hover:text-zinc-200"
              }`}
            >
              <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
              </svg>
              <span>Einstellungen</span>
            </button>
            <button
              onClick={() => setActiveTab("system")}
              className={`pb-3 px-1 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 ${
                activeTab === "system"
                  ? "theme-text-accent border-indigo-500"
                  : "text-zinc-400 border-transparent hover:text-zinc-200"
              }`}
            >
              <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
              </svg>
              <span>Systemeinstellungen</span>
            </button>
          </div>
        )}

        {/* General Settings Tab (User Preferences & Profile) */}
        {(activeTab === "general" || !currentUser.is_admin) && (
          <div className="space-y-8">
            {/* Theme & Style Selector Card */}
            <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
              <CardHeader>
                <CardTitle className="text-xl font-semibold flex items-center gap-2">
                  <svg className="w-5 h-5 fill-current text-indigo-400" viewBox="0 0 24 24">
                    <path d="M12 3c-4.97 0-9 4.03-9 9 0 2.12.74 4.07 1.97 5.61L4.35 20c-.17.38.16.8.56.7l2.45-.61C8.82 20.65 10.36 21 12 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm0 16c-1.44 0-2.81-.35-4.02-1l-.43-.24-1.2.3.3-1.18-.26-.45C5.7 15.25 5 13.68 5 12c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7z"/>
                  </svg>
                  <span>Design & Erscheinungsbild</span>
                </CardTitle>
                <CardDescription className="mt-1">
                  Wähle dein bevorzugtes UI-Design (z.B. Klassisch Hell, Dark Neon, Skandinavisch Warm) sowie deine Akzentfarbe. Jeder Benutzer kann sein persönliches Erscheinungsbild individuell festlegen.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* 1. Design-Stil Grid */}
                <div>
                  <Label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3 block">
                    1. Oberfläche & Design-Stil wählen:
                  </Label>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {STYLES.map(s => {
                      const isSelected = styleTheme === s.id;
                      return (
                        <button
                          key={s.id}
                          type="button"
                          onClick={() => setStyleTheme(s.id)}
                          className={`p-4 rounded-xl border text-left transition-all flex flex-col justify-between gap-3 relative overflow-hidden ${
                            isSelected
                              ? "border-indigo-500 bg-zinc-800/90 ring-2 ring-indigo-500/50 shadow-xl scale-[1.01]"
                              : "border-zinc-800/80 bg-zinc-950/50 hover:bg-zinc-800/50 hover:border-zinc-700"
                          }`}
                        >
                          {/* Mini Theme Preview */}
                          <div
                            className="w-full h-14 rounded-lg p-2 border flex flex-col justify-between"
                            style={{ backgroundColor: s.previewBg, borderColor: s.previewBorder }}
                          >
                            <div className="flex justify-between items-center">
                              <div
                                className="h-2 w-12 rounded"
                                style={{ backgroundColor: s.mode === "light" ? "#64748b" : "#a1a1aa" }}
                              ></div>
                              <span
                                className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold uppercase ${
                                  s.mode === "light"
                                    ? "bg-slate-200 text-slate-800 border border-slate-300"
                                    : "bg-zinc-800 text-zinc-300 border border-zinc-700"
                                }`}
                              >
                                {s.mode === "light" ? "☀️ HELL" : "🌙 DUNKEL"}
                              </span>
                            </div>
                            <div
                              className="h-5 w-full rounded border flex items-center px-2 text-[9px] font-mono shadow-sm"
                              style={{ backgroundColor: s.previewCard, borderColor: s.previewBorder, color: s.mode === "light" ? "#0f172a" : "#f8fafc" }}
                            >
                              <span className="truncate">Karte & Formular</span>
                            </div>
                          </div>

                          <div>
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-bold text-zinc-100">{s.name}</span>
                              {isSelected && <span className="text-xs text-indigo-400 font-bold">Aktiv ✓</span>}
                            </div>
                            <p className="text-xs text-zinc-400 leading-relaxed mt-1">{s.desc}</p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* 2. Color Accent Grid */}
                <div className="pt-4 border-t border-zinc-800/80">
                  <Label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3 block">
                    2. Akzentfarbe wählen:
                  </Label>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                    {THEMES.map(t => {
                      const isSelected = theme === t.id;
                      return (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => setTheme(t.id)}
                          className={`flex items-center gap-2.5 p-3 rounded-xl border text-left transition-all ${
                            isSelected
                              ? "border-zinc-400 bg-zinc-800/80 ring-2 ring-zinc-500/50 shadow-lg"
                              : "border-zinc-800/80 bg-zinc-950/40 hover:bg-zinc-800/40 hover:border-zinc-700"
                          }`}
                        >
                          <div
                            className="w-5 h-5 rounded-full flex items-center justify-center shadow-md shrink-0"
                            style={{ backgroundColor: t.color }}
                          >
                            {isSelected && (
                              <span className="text-white text-[10px] font-bold">✓</span>
                            )}
                          </div>
                          <span className="text-xs font-medium text-zinc-200 truncate">{t.name}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* User Profile & Single User Export Card */}
            <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
              <CardHeader>
                <CardTitle className="text-xl font-semibold">Persönliche Daten & Mein Daten-Backup</CardTitle>
                <CardDescription>Aktualisiere deine E-Mail-Adresse, ändere dein Passwort oder sichere alle deine Polizzen & Dokumente.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <form onSubmit={handleProfileSave} className="space-y-4 max-w-md">
                  <div className="space-y-2">
                    <Label htmlFor="email">E-Mail-Adresse</Label>
                    <Input
                      id="email"
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      required
                      className="bg-zinc-950/50 border-zinc-800"
                    />
                  </div>

                  <div className="space-y-2 pt-2">
                    <Label htmlFor="newPassword">Neues Passwort (optional)</Label>
                    <Input
                      id="newPassword"
                      type="password"
                      value={newPassword}
                      onChange={e => setNewPassword(e.target.value)}
                      placeholder="Unverändert lassen"
                      className="bg-zinc-950/50 border-zinc-800"
                    />
                  </div>

                  {newPassword && (
                    <div className="space-y-2">
                      <Label htmlFor="confirmPassword">Passwort bestätigen</Label>
                      <Input
                        id="confirmPassword"
                        type="password"
                        value={confirmPassword}
                        onChange={e => setConfirmPassword(e.target.value)}
                        className="bg-zinc-950/50 border-zinc-800"
                      />
                    </div>
                  )}

                  {profileMsg && (
                    <div className="p-3 bg-emerald-950/50 border border-emerald-800 text-emerald-300 rounded-lg text-sm">
                      {profileMsg}
                    </div>
                  )}

                  {profileErr && <p className="text-red-400 text-sm">{profileErr}</p>}

                  <div className="flex items-center gap-3 pt-2">
                    <Button type="submit" disabled={profileLoading} className="theme-bg-accent text-white theme-glow">
                      {profileLoading ? "Speichert..." : "Änderungen speichern"}
                    </Button>

                    <Button
                      type="button"
                      variant="outline"
                      disabled={exportingUserId === currentUser.id}
                      onClick={() => handleExportUser(currentUser.id, currentUser.email)}
                      className="border-zinc-700 bg-zinc-900 text-zinc-300 text-xs hover:bg-zinc-800"
                    >
                      {exportingUserId === currentUser.id ? "Erstelle Backup..." : "📤 Meine Daten exportieren (.noxususer)"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        )}

        {/* System Settings Tab (Admin Only) */}
        {currentUser.is_admin && activeTab === "system" && (
          <div className="space-y-8">
            {/* AI OCR Engine Settings Card */}
            <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
              <CardHeader>
                <CardTitle className="text-xl font-semibold flex items-center gap-2">
                  <svg className="w-5 h-5 fill-current text-purple-400" viewBox="0 0 24 24">
                    <path d="M20 2H4c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM9 17H7v-2h2v2zm0-4H7v-2h2v2zm0-4H7V7h2v2zm4 8h-2v-2h2v2zm0-4h-2v-2h2v2zm0-4h-2V7h2v2zm4 8h-2v-2h2v2zm0-4h-2v-2h2v2zm0-4h-2V7h2v2z"/>
                  </svg>
                  <span>🤖 KI-gestützte Dokumentenanalyse & OCR Engine</span>
                </CardTitle>
                <CardDescription className="mt-1">
                  Wähle zwischen der lokalen KI (Qwen2.5 1.5B) zur präzisen Vertragsanalyse oder der klassischen regelbasierten OCR-Erkennung.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <form onSubmit={handleSaveAiConfig} className="space-y-5">
                  <div className="flex items-center space-x-3 p-4 rounded-xl bg-zinc-950/60 border border-zinc-800">
                    <input
                      type="checkbox"
                      id="useAiOcr"
                      checked={useAiOcr}
                      onChange={e => setUseAiOcr(e.target.checked)}
                      className="w-5 h-5 rounded border-zinc-700 bg-zinc-900 text-purple-600 focus:ring-purple-500 accent-purple-600 cursor-pointer"
                    />
                    <Label htmlFor="useAiOcr" className="text-sm font-semibold text-white cursor-pointer select-none">
                      Lokale KI-Analyse aktivieren (Qwen2.5 1.5B via Llama-cpp)
                    </Label>
                  </div>

                  {/* Recommended Hardware Info Box */}
                  <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-800/40 text-purple-200 space-y-2 text-xs leading-relaxed">
                    <h4 className="font-bold text-purple-300 uppercase tracking-wider text-[11px]">
                      💡 Empfohlene Hardware-Ressourcen für KI-Nutzung:
                    </h4>
                    <ul className="list-disc list-inside space-y-1 text-zinc-300 font-mono text-[11px]">
                      <li><strong>Prozessor (CPU):</strong> Mindestens <strong>4 CPU-Kerne</strong> (mit AVX2-Befehlssatz).</li>
                      <li><strong>Arbeitsspeicher (RAM):</strong> Mindestens <strong>4 GB RAM</strong> (Modell benötigt ~1,2 GB freien RAM).</li>
                      <li><strong>Festplattenspeicher:</strong> ca. <strong>1 GB</strong> für die lokalen Modellgewichtungen.</li>
                    </ul>
                    <p className="text-zinc-400 text-[11px] pt-1">
                      <em>Hinweis bei schwächeren Systemen:</em> Auf Servern mit unter 4 GB RAM oder 2 CPU-Kernen empfiehlt es sich, die KI zu deaktivieren. Das System nutzt dann automatisch die superschnelle klassische OCR-Erkennung ohne KI-Modell.
                    </p>
                  </div>

                  {aiConfigMsg && (
                    <div className="p-3 bg-emerald-950/50 border border-emerald-800 text-emerald-300 rounded-xl text-xs">
                      {aiConfigMsg}
                    </div>
                  )}
                  {aiConfigErr && (
                    <div className="p-3 bg-red-950/50 border border-red-800 text-red-300 rounded-xl text-xs">
                      {aiConfigErr}
                    </div>
                  )}

                  <div className="flex justify-end pt-2 border-t border-zinc-800/80">
                    <Button type="submit" disabled={aiConfigSaving} className="theme-bg-accent text-white theme-glow text-xs font-medium">
                      {aiConfigSaving ? "Speichert..." : "KI-Einstellungen speichern"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>

            {/* Automated Scheduled Backups Configuration Card */}
            <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
              <CardHeader>
                <CardTitle className="text-xl font-semibold flex items-center gap-2">
                  <svg className="w-5 h-5 fill-current text-zinc-400" viewBox="0 0 24 24">
                    <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm4.2 14.2L11 13V7h1.5v5.2l4.5 2.7-.8 1.3z"/>
                  </svg>
                  <span>Automatisierte Zeitplan-Backups & Aufbewahrungsregeln</span>
                </CardTitle>
                <CardDescription className="mt-1">
                  Stelle ein, wann automatische Voll-Backups erstellt und nach wie vielen Tagen oder wie vielen Sicherungen sie automatisch bereinigt werden.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <form onSubmit={handleSaveAutoBackupConfig} className="space-y-5">
                  <div className="flex items-center space-x-3 p-3.5 rounded-xl bg-zinc-950/60 border border-zinc-800">
                    <input
                      type="checkbox"
                      id="autoBackupEnabled"
                      checked={autoBackupEnabled}
                      onChange={e => setAutoBackupEnabled(e.target.checked)}
                      className="w-5 h-5 rounded border-zinc-700 bg-zinc-900 text-indigo-600 focus:ring-indigo-500 accent-indigo-600 cursor-pointer"
                    />
                    <Label htmlFor="autoBackupEnabled" className="text-sm font-medium text-white cursor-pointer select-none">
                      Automatische System-Backups aktivieren
                    </Label>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="autoBackupInterval" className="text-xs font-mono text-zinc-400">Intervall</Label>
                      <select
                        id="autoBackupInterval"
                        value={autoBackupInterval}
                        onChange={e => setAutoBackupInterval(e.target.value)}
                        className="w-full h-9 rounded-md bg-zinc-950/60 border border-zinc-800 text-xs px-3 text-zinc-200 focus:outline-none focus:ring-1 focus:ring-zinc-700"
                      >
                        <option value="daily">Täglich</option>
                        <option value="3days">Alle 3 Tage</option>
                        <option value="weekly">Wöchentlich (alle 7 Tage)</option>
                        <option value="30days">Alle 30 Tage</option>
                      </select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="autoBackupTime" className="text-xs font-mono text-zinc-400">Ausführungs-Uhrzeit</Label>
                      <Input
                        id="autoBackupTime"
                        type="time"
                        value={autoBackupTime}
                        onChange={e => setAutoBackupTime(e.target.value)}
                        className="bg-zinc-950/60 border-zinc-800 font-mono text-xs"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="autoBackupPassword" className="text-xs font-mono text-zinc-400">Verschlüsselungs-Passwort</Label>
                      <Input
                        id="autoBackupPassword"
                        type="password"
                        value={autoBackupPassword}
                        onChange={e => setAutoBackupPassword(e.target.value)}
                        placeholder="Passwort für AES-256 Schutz"
                        className="bg-zinc-950/60 border-zinc-800 text-xs"
                      />
                    </div>
                  </div>

                  {/* Retention Rules */}
                  <div className="p-4 rounded-xl bg-zinc-950/40 border border-zinc-800 space-y-4">
                    <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider">Automatisches Löschen & Aufbewahrung (Retention)</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="autoBackupRetentionDays" className="text-xs text-zinc-400">Auto-Löschung nach X Tagen (0 = nie löschen)</Label>
                        <Input
                          id="autoBackupRetentionDays"
                          type="number"
                          min="0"
                          value={autoBackupRetentionDays}
                          onChange={e => setAutoBackupRetentionDays(e.target.value)}
                          placeholder="z. B. 14 Tage"
                          className="bg-zinc-950/60 border-zinc-800 text-xs"
                        />
                        <p className="text-[11px] text-zinc-500">Ältere Backups als diese Anzahl an Tagen werden automatisch vom Server gelöscht.</p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="autoBackupRetentionCount" className="text-xs text-zinc-400">Maximal X Backups behalten (0 = unbegrenzt)</Label>
                        <Input
                          id="autoBackupRetentionCount"
                          type="number"
                          min="0"
                          value={autoBackupRetentionCount}
                          onChange={e => setAutoBackupRetentionCount(e.target.value)}
                          placeholder="z. B. 10 Stück"
                          className="bg-zinc-950/60 border-zinc-800 text-xs"
                        />
                        <p className="text-[11px] text-zinc-500">Wenn mehr Backups existieren, werden die ältesten automatisch gelöscht.</p>
                      </div>
                    </div>
                  </div>

                  {autoBackupLastRun && (
                    <p className="text-xs text-zinc-400 font-mono">
                      Letzte automatische Backup-Ausführung: {new Date(autoBackupLastRun).toLocaleString("de-DE")}
                    </p>
                  )}

                  {autoBackupMsg && (
                    <div className="p-3 bg-emerald-950/50 border border-emerald-800 text-emerald-300 rounded-xl text-xs">
                      {autoBackupMsg}
                    </div>
                  )}
                  {autoBackupErr && (
                    <div className="p-3 bg-red-950/50 border border-red-800 text-red-300 rounded-xl text-xs">
                      {autoBackupErr}
                    </div>
                  )}

                  <div className="flex justify-between items-center pt-2 border-t border-zinc-800/80 gap-3">
                    <Button
                      type="button"
                      variant="outline"
                      disabled={autoBackupRunning}
                      onClick={handleRunBackupNow}
                      className="border-indigo-800 bg-indigo-950/50 hover:bg-indigo-900 text-indigo-300 text-xs"
                    >
                      {autoBackupRunning ? "Erstelle Backup..." : "⚡ Sofort Backup auf Server erstellen"}
                    </Button>

                    <Button type="submit" disabled={autoBackupSaving} className="theme-bg-accent text-white theme-glow text-xs font-medium">
                      {autoBackupSaving ? "Speichert..." : "Zeitplan & Regeln speichern"}
                    </Button>
                  </div>
                </form>

                {/* Stored Server Backups Table */}
                <div className="pt-6 border-t border-zinc-800/80 space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <svg className="w-4 h-4 fill-current text-zinc-400" viewBox="0 0 24 24">
                        <path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/>
                      </svg>
                      <span>Gespeicherte Server-Backups ({storedBackups.length})</span>
                    </h3>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={loadStoredBackupsList}
                      className="text-xs border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300"
                    >
                      🔄 Liste aktualisieren
                    </Button>
                  </div>

                  {loadingStoredBackups ? (
                    <p className="text-xs text-zinc-500 py-4 text-center">Lade gespeicherte Backups...</p>
                  ) : storedBackups.length === 0 ? (
                    <p className="text-xs text-zinc-500 py-4 text-center">Noch keine Backups auf dem Server vorhanden.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs text-zinc-300">
                        <thead className="bg-zinc-950/60 text-zinc-400 uppercase font-mono border-b border-zinc-800">
                          <tr>
                            <th className="px-3 py-2.5">Typ</th>
                            <th className="px-3 py-2.5">Dateiname</th>
                            <th className="px-3 py-2.5">Erstellt am</th>
                            <th className="px-3 py-2.5">Größe</th>
                            <th className="px-3 py-2.5 text-right">Aktionen</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/50">
                          {storedBackups.map(b => (
                            <tr key={b.filename} className="hover:bg-zinc-800/30 transition-colors">
                              <td className="px-3 py-2.5 font-medium">
                                <span className={`px-2 py-0.5 rounded text-[10px] ${
                                  b.type === "Manuell" ? "bg-indigo-950 text-indigo-300 border border-indigo-800" : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                }`}>
                                  {b.type}
                                </span>
                              </td>
                              <td className="px-3 py-2.5 font-mono text-zinc-200">{b.filename}</td>
                              <td className="px-3 py-2.5 text-zinc-400">{new Date(b.created_at).toLocaleString("de-DE")}</td>
                              <td className="px-3 py-2.5 font-mono text-zinc-400">{b.size_mb} MB</td>
                              <td className="px-3 py-2.5 text-right">
                                <div className="flex items-center justify-end gap-2">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleDownloadStoredBackup(b.filename)}
                                    className="border-zinc-700 bg-zinc-900 text-[11px] hover:bg-zinc-800 text-zinc-200 h-7 px-2"
                                    title="Herunterladen"
                                  >
                                    ⬇️ Download
                                  </Button>

                                  <Button
                                    size="sm"
                                    variant="outline"
                                    disabled={restoringFilename === b.filename}
                                    onClick={() => handleRestoreStoredBackup(b.filename)}
                                    className="border-amber-800 bg-amber-950/50 text-[11px] hover:bg-amber-900 text-amber-300 h-7 px-2"
                                    title="Einspielen"
                                  >
                                    {restoringFilename === b.filename ? "Spielt ein..." : "📥 Wiederherstellen"}
                                  </Button>

                                  <Button
                                    size="sm"
                                    variant="destructive"
                                    disabled={deletingFilename === b.filename}
                                    onClick={() => handleDeleteStoredBackup(b.filename)}
                                    className="bg-red-950/80 hover:bg-red-900 text-red-300 border border-red-800 text-[11px] h-7 px-2"
                                    title="Löschen"
                                  >
                                    {deletingFilename === b.filename ? "Löscht..." : "🗑️"}
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Manually Export / Import Encrypted System Backup File */}
            <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
              <CardHeader>
                <CardTitle className="text-xl font-semibold flex items-center gap-2">
                  <svg className="w-5 h-5 fill-current text-zinc-400" viewBox="0 0 24 24">
                    <path d="M20 6h-8l-2-2H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-5 11H9v-2h6v2zm3-4H6V9h12v4z"/>
                  </svg>
                  <span>Manuelles Vollsystem-Backup Export / Import</span>
                </CardTitle>
                <CardDescription className="mt-1">
                  Exportiere manuell eine verschlüsselte `.noxusbackup` Datei auf deinen Computer oder lade eine Sicherungsdatei hoch.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                {/* Export Section */}
                <div className="space-y-4 pb-6 border-b border-zinc-800/80">
                  <div className="space-y-1">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <svg className="w-4 h-4 fill-current text-zinc-400" viewBox="0 0 24 24">
                        <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/>
                      </svg>
                      <span>1. Manuelles Vollsystem-Backup auf PC herunterladen</span>
                    </h3>
                  </div>

                  <form onSubmit={handleExportBackup} className="space-y-4 max-w-lg">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="backupExportPassword" className="text-xs font-mono text-zinc-400">Backup-Passwort</Label>
                        <Input
                          id="backupExportPassword"
                          type="password"
                          value={backupExportPassword}
                          onChange={e => setBackupExportPassword(e.target.value)}
                          placeholder="••••••••"
                          required
                          className="bg-zinc-950/60 border-zinc-800 text-xs"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="backupExportConfirm" className="text-xs font-mono text-zinc-400">Passwort wiederholen</Label>
                        <Input
                          id="backupExportConfirm"
                          type="password"
                          value={backupExportConfirm}
                          onChange={e => setBackupExportConfirm(e.target.value)}
                          placeholder="••••••••"
                          required
                          className="bg-zinc-950/60 border-zinc-800 text-xs"
                        />
                      </div>
                    </div>

                    {backupExportMsg && (
                      <div className="p-3 bg-emerald-950/50 border border-emerald-800 text-emerald-300 rounded-xl text-xs">
                        {backupExportMsg}
                      </div>
                    )}
                    {backupExportErr && (
                      <div className="p-3 bg-red-950/50 border border-red-800 text-red-300 rounded-xl text-xs">
                        {backupExportErr}
                      </div>
                    )}

                    <Button
                      type="submit"
                      disabled={backupExporting}
                      className="theme-bg-accent text-white theme-glow text-xs font-medium"
                    >
                      {backupExporting ? "Erstelle verschlüsseltes Backup..." : "Backup herunterladen (.noxusbackup)"}
                    </Button>
                  </form>
                </div>

                {/* Import / Restore Section */}
                <div className="space-y-4">
                  <div className="space-y-1">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <svg className="w-4 h-4 fill-current text-zinc-400" viewBox="0 0 24 24">
                        <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
                      </svg>
                      <span>2. Vollsystem-Backup-Datei vom PC hochladen & wiederherstellen</span>
                    </h3>
                  </div>

                  <form onSubmit={handleImportBackup} className="space-y-4 max-w-lg">
                    <div className="space-y-2">
                      <Label htmlFor="backupImportFile" className="text-xs font-mono text-zinc-400">Backup-Datei (.noxusbackup)</Label>
                      <Input
                        id="backupImportFile"
                        type="file"
                        accept=".noxusbackup"
                        onChange={e => setBackupImportFile(e.target.files?.[0] || null)}
                        required
                        className="bg-zinc-950/60 border-zinc-800 text-xs file:bg-zinc-900 file:text-zinc-300 file:border-0 file:rounded-md file:px-2 file:py-1 file:mr-3"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="backupImportPassword" className="text-xs font-mono text-zinc-400">Entschlüsselungs-Passwort</Label>
                      <Input
                        id="backupImportPassword"
                        type="password"
                        value={backupImportPassword}
                        onChange={e => setBackupImportPassword(e.target.value)}
                        placeholder="Gleiches Passwort wie beim Export"
                        required
                        className="bg-zinc-950/60 border-zinc-800 text-xs"
                      />
                    </div>

                    <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-800/60 text-amber-300 text-xs">
                      <strong>Achtung:</strong> Beim Importieren wird der Datenbestand auf diesem Server mit den gesicherten Daten überschrieben!
                    </div>

                    {backupImportMsg && (
                      <div className="p-3 bg-emerald-950/50 border border-emerald-800 text-emerald-300 rounded-xl text-xs">
                        {backupImportMsg}
                      </div>
                    )}
                    {backupImportErr && (
                      <div className="p-3 bg-red-950/50 border border-red-800 text-red-300 rounded-xl text-xs">
                        {backupImportErr}
                      </div>
                    )}

                    <Button
                      type="submit"
                      disabled={backupImporting}
                      className="bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs shadow-lg"
                    >
                      {backupImporting ? "Entschlüssele & stelle wieder her..." : "Backup wiederherstellen"}
                    </Button>
                  </form>
                </div>
              </CardContent>
            </Card>

            {/* Admin Dynamic SMTP Settings */}
            <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
              <CardHeader>
                <div>
                  <CardTitle className="text-xl font-semibold flex items-center gap-2">
                    <svg className="w-5 h-5 fill-current text-zinc-400" viewBox="0 0 24 24">
                      <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
                    </svg>
                    <span>E-Mail & SMTP Server Einstellungen</span>
                  </CardTitle>
                  <CardDescription className="mt-1">
                    Konfiguriere den SMTP-Mailserver für Passwort-Resets und System-Benachrichtigungen.
                  </CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSmtpSave} className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="appUrl" className="text-xs font-mono text-zinc-400">Öffentliche Anwendungs-URL (für Links in E-Mails)</Label>
                    <Input
                      id="appUrl"
                      value={appUrl}
                      onChange={e => setAppUrl(e.target.value)}
                      placeholder="http://192.168.1.251:3000"
                      className="bg-zinc-950/60 border-zinc-800 font-mono text-xs"
                    />
                    <p className="text-[11px] text-zinc-500">Diese Adresse (z. B. http://192.168.1.251:3000) wird in Passwort-Reset E-Mails als Ziel-Link verwendet.</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2 md:col-span-2">
                      <Label htmlFor="smtpServer" className="text-xs font-mono text-zinc-400">SMTP Host / Server</Label>
                      <Input
                        id="smtpServer"
                        value={smtpServer}
                        onChange={e => setSmtpServer(e.target.value)}
                        placeholder="z.B. smtp.gmail.com oder mail.gmx.net"
                        className="bg-zinc-950/60 border-zinc-800 font-mono text-xs"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="smtpPort" className="text-xs font-mono text-zinc-400">Port</Label>
                      <Input
                        id="smtpPort"
                        value={smtpPort}
                        onChange={e => setSmtpPort(e.target.value)}
                        placeholder="587, 465"
                        className="bg-zinc-950/60 border-zinc-800 font-mono text-xs"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="smtpFrom" className="text-xs font-mono text-zinc-400">Absender E-Mail-Adresse (From)</Label>
                    <Input
                      id="smtpFrom"
                      value={smtpFrom}
                      onChange={e => setSmtpFrom(e.target.value)}
                      placeholder="no-reply@deinedomain.de"
                      className="bg-zinc-950/60 border-zinc-800 text-xs"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="smtpUsername" className="text-xs font-mono text-zinc-400">SMTP Benutzername (optional)</Label>
                      <Input
                        id="smtpUsername"
                        value={smtpUsername}
                        onChange={e => setSmtpUsername(e.target.value)}
                        placeholder="deine-mail@domain.de"
                        className="bg-zinc-950/60 border-zinc-800 text-xs"
                      />
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <Label htmlFor="smtpPassword" className="text-xs font-mono text-zinc-400">SMTP Passwort (optional)</Label>
                        <button
                          type="button"
                          onClick={() => setShowSmtpPassword(!showSmtpPassword)}
                          className="text-[11px] text-zinc-400 hover:text-white"
                        >
                          {showSmtpPassword ? "Verbergen" : "Anzeigen"}
                        </button>
                      </div>
                      <Input
                        id="smtpPassword"
                        type={showSmtpPassword ? "text" : "password"}
                        value={smtpPassword}
                        onChange={e => setSmtpPassword(e.target.value)}
                        placeholder="••••••••"
                        className="bg-zinc-950/60 border-zinc-800 text-xs"
                      />
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 pt-1">
                    <input
                      type="checkbox"
                      id="smtpUseTls"
                      checked={smtpUseTls}
                      onChange={e => setSmtpUseTls(e.target.checked)}
                      className="w-4 h-4 rounded border-zinc-700 bg-zinc-950 text-indigo-600 focus:ring-indigo-500 accent-indigo-600 cursor-pointer"
                    />
                    <Label htmlFor="smtpUseTls" className="text-xs text-zinc-300 cursor-pointer select-none">
                      STARTTLS / SSL Verschlüsselung aktivieren (empfohlen für Port 587 & 465)
                    </Label>
                  </div>

                  {smtpMsg && (
                    <div className="p-3 bg-emerald-950/50 border border-emerald-800 text-emerald-300 rounded-xl text-xs">
                      {smtpMsg}
                    </div>
                  )}
                  {smtpErr && (
                    <div className="p-3 bg-red-950/50 border border-red-800 text-red-300 rounded-xl text-xs">
                      {smtpErr}
                    </div>
                  )}

                  <div className="flex justify-between items-center pt-2 border-t border-zinc-800/80 gap-3">
                    <Button
                      type="button"
                      variant="outline"
                      disabled={smtpTesting}
                      onClick={handleSmtpTest}
                      className="border-indigo-800 bg-indigo-950/50 hover:bg-indigo-900 text-indigo-300 text-xs"
                    >
                      {smtpTesting ? "Testet..." : "🧪 Test-E-Mail senden"}
                    </Button>

                    <Button type="submit" disabled={smtpSaving} className="theme-bg-accent text-white theme-glow text-xs font-medium">
                      {smtpSaving ? "Speichert..." : "SMTP-Einstellungen speichern"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>

            {/* Admin User Management Section */}
            <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-xl font-semibold flex items-center gap-2">
                      <svg className="w-5 h-5 fill-current text-zinc-400" viewBox="0 0 24 24">
                        <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
                      </svg>
                      <span>Benutzerverwaltung & Einzel-Import</span>
                    </CardTitle>
                    <CardDescription className="mt-1">
                      Alle registrierten Benutzer verwalten, einzeln sichern oder eine `.noxususer` Sicherung importieren.
                    </CardDescription>
                  </div>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowUserImportBox(!showUserImportBox)}
                    className="border-indigo-800 bg-indigo-950/50 text-indigo-300 text-xs hover:bg-indigo-900"
                  >
                    📥 Einzelnen Benutzer importieren (.noxususer)
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Collapsible Single User Import Box */}
                {showUserImportBox && (
                  <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800 space-y-3">
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">Benutzer-Backup importieren (.noxususer)</h4>
                    <p className="text-xs text-zinc-400">Importiert den Benutzer samt allen Polizzen, Stammdaten und Dokumenten. Falls der Benutzer bereits existiert, werden die Polizzen zugeordnet.</p>
                    
                    <form onSubmit={handleImportUserSubmit} className="space-y-3 max-w-md">
                      <div className="space-y-1">
                        <Label htmlFor="userImportFile" className="text-xs text-zinc-400">Benutzer-Sicherungsdatei (.noxususer)</Label>
                        <Input
                          id="userImportFile"
                          type="file"
                          accept=".noxususer"
                          onChange={e => setUserImportFile(e.target.files?.[0] || null)}
                          required
                          className="bg-zinc-950 border-zinc-800 text-xs file:bg-zinc-900 file:text-zinc-300 file:border-0 file:rounded-md file:px-2 file:py-1 file:mr-3"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor="userImportPassword" className="text-xs text-zinc-400">Entschlüsselungs-Passwort</Label>
                        <Input
                          id="userImportPassword"
                          type="password"
                          value={userImportPassword}
                          onChange={e => setUserImportPassword(e.target.value)}
                          placeholder="Passwort beim Export"
                          required
                          className="bg-zinc-950 border-zinc-800 text-xs"
                        />
                      </div>

                      {userImportMsg && (
                        <div className="p-2 bg-emerald-950/50 border border-emerald-800 text-emerald-300 rounded text-xs">
                          {userImportMsg}
                        </div>
                      )}
                      {userImportErr && (
                        <div className="p-2 bg-red-950/50 border border-red-800 text-red-300 rounded text-xs">
                          {userImportErr}
                        </div>
                      )}

                      <Button type="submit" disabled={userImporting} className="theme-bg-accent text-white theme-glow text-xs">
                        {userImporting ? "Importiere Benutzer..." : "📥 Benutzer jetzt importieren"}
                      </Button>
                    </form>
                  </div>
                )}

                {adminMsg && (
                  <div className="p-3 bg-emerald-950/50 border border-emerald-800 text-emerald-300 rounded-lg text-sm">
                    {adminMsg}
                  </div>
                )}
                {adminErr && (
                  <div className="p-3 bg-red-950/50 border border-red-800 text-red-300 rounded-lg text-sm">
                    {adminErr}
                  </div>
                )}

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-zinc-300">
                    <thead className="bg-zinc-950/50 text-zinc-400 uppercase text-xs border-b border-zinc-800">
                      <tr>
                        <th className="px-4 py-3">ID</th>
                        <th className="px-4 py-3">E-Mail / Benutzername</th>
                        <th className="px-4 py-3">Rolle</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3 text-right">Aktionen</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/50">
                      {allUsers.map(u => (
                        <tr key={u.id} className="hover:bg-zinc-800/30 transition-colors">
                          <td className="px-4 py-3 font-mono text-zinc-500">{u.id}</td>
                          <td className="px-4 py-3 font-medium text-zinc-200">{u.email}</td>
                          <td className="px-4 py-3">
                            {u.is_admin ? (
                              <span className="px-2 py-0.5 rounded text-xs bg-zinc-800 text-zinc-200 border border-zinc-700">
                                Admin
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded text-xs bg-zinc-900 text-zinc-400">
                                Benutzer
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {u.must_change_password ? (
                              <span className="text-amber-400 text-xs">Ersteinrichtung ausstehend</span>
                            ) : (
                              <span className="text-emerald-400 text-xs">Aktiv</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={exportingUserId === u.id}
                                onClick={() => handleExportUser(u.id, u.email)}
                                className="border-indigo-800 bg-indigo-950/50 text-xs hover:bg-indigo-900 text-indigo-300"
                                title="Sichert diesen Benutzer samt allen Polizzen & Dokumenten"
                              >
                                {exportingUserId === u.id ? "Exportiert..." : "📤 Export"}
                              </Button>

                              <Button
                                size="sm"
                                variant="outline"
                                disabled={sendingEmailId === u.id}
                                onClick={() => handleSendResetEmail(u.email, u.id)}
                                className="border-zinc-700 bg-zinc-900 text-xs hover:bg-zinc-800 text-zinc-300"
                              >
                                {sendingEmailId === u.id ? "Sendet..." : "Passwort-Reset"}
                              </Button>

                              <Button
                                size="sm"
                                variant="destructive"
                                disabled={deletingUserId === u.id || u.id === currentUser.id}
                                onClick={() => handleDeleteUser(u)}
                                className="bg-red-950/80 hover:bg-red-900 text-red-300 border border-red-800 text-xs"
                              >
                                {deletingUserId === u.id ? "Löscht..." : "Löschen"}
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
