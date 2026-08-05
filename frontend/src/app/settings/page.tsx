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
import { APP_VERSION } from "@/lib/version";
import { 
  RefreshCw, CheckCircle2, AlertCircle, Loader2, 
  Settings, Wrench, Palette, Calendar, Cpu, Clock, 
  Database, Mail, Users, ArrowLeft 
} from "lucide-react";

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
  const { theme, setTheme, styleTheme, setStyleTheme, showCostChart, setShowCostChart } = useTheme();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [activeTab, setActiveTab] = useState<"general" | "system">("general");
  
  // Profile form
  const [email, setEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [emailNotificationsEnabled, setEmailNotificationsEnabled] = useState(true);
  const [isSmtpConfigured, setIsSmtpConfigured] = useState(false);
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

  // Live Calendar Token State
  const [calendarToken, setCalendarToken] = useState("");
  const [calendarTokenLoading, setCalendarTokenLoading] = useState(false);
  const [calendarTokenMsg, setCalendarTokenMsg] = useState("");
  const [webcalEnabled, setWebcalEnabled] = useState(false);
  const [webcalSaving, setWebcalSaving] = useState(false);
  const [webcalMsg, setWebcalMsg] = useState("");

  // System Update State
  const [isUpdating, setIsUpdating] = useState(false);
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [updateStatusMsg, setUpdateStatusMsg] = useState("Update wird gestartet...");
  const [updateError, setUpdateError] = useState("");
  const [updateSuccess, setUpdateSuccess] = useState(false);

  const handleTriggerSystemUpdate = async () => {
    if (!window.confirm("Möchtest du das System-Update wirklich jetzt ausführen? Ein Sicherheits-Backup der Datenbank wird vorab automatisch erstellt.")) {
      return;
    }

    setIsUpdating(true);
    setShowUpdateModal(true);
    setUpdateError("");
    setUpdateSuccess(false);
    setUpdateStatusMsg("Starte System-Update... Der Server lädt den neuesten Stand von GitHub herunter.");

    try {
      await api.post("/backup/trigger-system-update", {});
    } catch (err: any) {
      console.warn("Update trigger notice:", err);
    }

    let attempts = 0;
    const maxAttempts = 100; // 5 minutes max timeout as requested
    let hasServerGoneDown = false;

    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const authHeaders = {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };

    const pollInterval = setInterval(async () => {
      attempts++;

      try {
        const sRes = await fetch("/api/backup/system-update-status", { cache: "no-store", headers: authHeaders });
        if (sRes.ok) {
          const statusRes = await sRes.json();
          if (statusRes && statusRes.status === "failed") {
            clearInterval(pollInterval);
            setIsUpdating(false);
            setUpdateError(statusRes.message || "Update fehlgeschlagen.");
            return;
          } else if (statusRes && statusRes.status === "completed" && (hasServerGoneDown || attempts > 5)) {
            clearInterval(pollInterval);
            setUpdateSuccess(true);
            setUpdateStatusMsg("✓ System-Update erfolgreich abgeschlossen! Seite wird neu geladen...");
            setTimeout(() => {
              window.location.reload();
            }, 2000);
            return;
          } else if (statusRes && statusRes.message && !hasServerGoneDown) {
            setUpdateStatusMsg(statusRes.message);
          }
        } else {
          // HTTP 502/503 while container is restarting
          hasServerGoneDown = true;
          setUpdateStatusMsg(`Server baut Docker-Container neu auf (kann 3-8 Min. dauern)... Warte auf Server-Neustart (${attempts}/${maxAttempts})...`);
        }
      } catch (e) {
        // Network error / Connection refused while backend container is restarting
        hasServerGoneDown = true;
        setUpdateStatusMsg(`Server baut Docker-Container neu auf (kann 3-8 Min. dauern)... Warte auf Server-Neustart (${attempts}/${maxAttempts})...`);
      }

      if (hasServerGoneDown) {
        try {
          const hRes = await fetch("/api/health", { cache: "no-store" });
          if (hRes.ok) {
            clearInterval(pollInterval);
            setUpdateSuccess(true);
            setUpdateStatusMsg("✓ Server ist wieder online! Seite wird neu geladen...");
            setTimeout(() => {
              window.location.reload();
            }, 2000);
            return;
          }
        } catch (e) {
          // Still rebuilding
        }
      }

      if (attempts >= maxAttempts) {
        clearInterval(pollInterval);
        setIsUpdating(false);
        setUpdateError("Zeitüberschreitung beim Warten auf den Server-Rebuild. Bitte prüfe dein Terminal oder lade die Seite manuell neu.");
      }
    }, 3000);
  };

  useEffect(() => {
    loadUserData();
  }, []);

  const loadCalendarToken = async () => {
    try {
      const res = await api.get("/users/calendar-token");
      if (res && res.calendar_token) {
        setCalendarToken(res.calendar_token);
      }
    } catch (e) {
      console.error("Error loading calendar token:", e);
    }
  };

  const loadWebCalConfig = async () => {
    try {
      const cfg = await api.get("/users/webcal-config");
      setWebcalEnabled(!!cfg.enabled);
    } catch (e) {
      console.error("Error loading webcal config:", e);
    }
  };

  const handleSaveWebCalConfig = async (val: boolean) => {
    setWebcalSaving(true);
    setWebcalMsg("");
    setWebcalEnabled(val);
    try {
      const res = await api.put("/users/webcal-config", { enabled: val });
      setWebcalMsg(res.msg || "Einstellung gespeichert!");
      setTimeout(() => setWebcalMsg(""), 3000);
    } catch (e: any) {
      alert(e.message || "Fehler beim Speichern der WebCal-Einstellung.");
    } finally {
      setWebcalSaving(false);
    }
  };

  const handleDownloadManualIcs = async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("/api/users/calendar/export.ics", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Fehler beim Erstellen der Kalenderdatei.");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "noxus_policy_kuendigungsfristen.ics";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || "Fehler beim Herunterladen des Kalenders.");
    }
  };

  const handleRotateCalendarToken = async () => {
    if (!window.confirm("Möchtest du deinen persönlichen Kalender-Token wirklich erneuern? Bestehende Kalender-Abonnements auf deinen Geräten müssen danach einmalig aktualisiert werden.")) return;
    setCalendarTokenLoading(true);
    setCalendarTokenMsg("");
    try {
      const res = await api.post("/users/calendar-token/rotate", {});
      setCalendarToken(res.calendar_token);
      setCalendarTokenMsg("Neuer Kalender-Token generiert!");
      setTimeout(() => setCalendarTokenMsg(""), 3500);
    } catch (e: any) {
      alert(e.message || "Fehler beim Erneuern des Tokens.");
    } finally {
      setCalendarTokenLoading(false);
    }
  };

  const loadUserData = async () => {
    try {
      const user = await api.get("/users/me");
      setCurrentUser(user);
      setEmail(user.email);
      setEmailNotificationsEnabled(user.email_notifications_enabled ?? true);
      loadCalendarToken();
      loadWebCalConfig();

      try {
        const smtpStatus = await api.get("/users/smtp-status");
        setIsSmtpConfigured(!!smtpStatus.configured);
      } catch (e) {
        setIsSmtpConfigured(false);
      }

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
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800/80 pb-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">Einstellungen</h1>
            <p className="text-xs sm:text-sm text-zinc-400 mt-1">
              {currentUser.is_admin 
                ? "Verwalte dein Konto, Farbschema sowie administrative Systemeinstellungen" 
                : "Verwalte dein Konto und Farbschema"}
            </p>
          </div>
          <Button variant="outline" onClick={() => router.push("/")} className="border-zinc-800 bg-zinc-900/50 hover:bg-zinc-800 text-zinc-300 text-xs sm:text-sm self-start sm:self-auto shrink-0">
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
              <Settings className="w-4 h-4 text-zinc-400" />
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
              <Wrench className="w-4 h-4 text-zinc-400" />
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
                  <Palette className="w-5 h-5 text-zinc-400" />
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

                {/* 3. Dashboard-Elemente & Diagramm Toggle */}
                <div className="pt-4 border-t border-zinc-800/80">
                  <Label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3 block">
                    3. Dashboard-Elemente & Diagramme:
                  </Label>
                  <div className="flex items-center justify-between p-4 rounded-xl bg-zinc-950/60 border border-zinc-800">
                    <div>
                      <Label htmlFor="showCostChartToggle" className="text-sm font-semibold text-white cursor-pointer">
                        📊 Sparten- & Kosten-Diagramm auf dem Dashboard anzeigen
                      </Label>
                      <p className="text-xs text-zinc-400 mt-1">
                        Aktiviert die visuelle Aufschlüsselung der jährlichen Versicherungskosten nach Sparten im Dashboard.
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      id="showCostChartToggle"
                      checked={showCostChart}
                      onChange={(e) => setShowCostChart(e.target.checked)}
                      className="w-5 h-5 accent-indigo-500 rounded cursor-pointer shrink-0"
                    />
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

                  {isSmtpConfigured ? (
                    <div className="pt-3 border-t border-zinc-800/80 space-y-2">
                      <div className="flex items-center justify-between p-3.5 rounded-xl bg-zinc-950/60 border border-zinc-800">
                        <div>
                          <Label htmlFor="emailNotificationsToggle" className="text-xs font-semibold text-white cursor-pointer block">
                            📧 E-Mail Benachrichtigungen für Kündigungsfristen
                          </Label>
                          <p className="text-[11px] text-zinc-400 mt-0.5">
                            Erhalte automatische Vorwarnungen per E-Mail, wenn eine Kündigungsfrist in den nächsten 30 Tagen abläuft.
                          </p>
                        </div>
                        <input
                          type="checkbox"
                          id="emailNotificationsToggle"
                          checked={emailNotificationsEnabled}
                          onChange={(e) => {
                            const val = e.target.checked;
                            setEmailNotificationsEnabled(val);
                            api.put("/users/profile", { email_notifications_enabled: val }).catch(console.error);
                          }}
                          className="w-4 h-4 accent-emerald-500 rounded cursor-pointer shrink-0 ml-3"
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="pt-3 border-t border-zinc-800/80">
                      <p className="text-xs text-zinc-400 flex items-center gap-2 bg-zinc-950/40 p-3 rounded-lg border border-zinc-800/60">
                        <span>ℹ️</span>
                        <span>
                          <strong>E-Mail-Benachrichtigungen:</strong> Diese Funktion wird automatisch hier sichtbar, sobald ein Administrator den SMTP-Server unter <em>Systemeinstellungen ➔ E-Mail & SMTP Server</em> konfiguriert hat.
                        </span>
                      </p>
                    </div>
                  )}

                  {profileMsg && (
                    <div className="p-3 bg-emerald-950/50 border border-emerald-800 text-emerald-300 rounded-lg text-sm">
                      {profileMsg}
                    </div>
                  )}

                  {profileErr && <p className="text-red-400 text-sm">{profileErr}</p>}

                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2 w-full">
                    <Button type="submit" disabled={profileLoading} className="theme-bg-accent text-white theme-glow w-full sm:w-auto">
                      {profileLoading ? "Speichert..." : "Änderungen speichern"}
                    </Button>

                    <Button
                      type="button"
                      variant="outline"
                      disabled={exportingUserId === currentUser.id}
                      onClick={() => handleExportUser(currentUser.id, currentUser.email)}
                      className="border-zinc-700 bg-zinc-900 text-zinc-300 text-xs hover:bg-zinc-800 w-full sm:w-auto"
                    >
                      {exportingUserId === currentUser.id ? "Erstelle Backup..." : "📤 Meine Daten exportieren (.noxususer)"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>

            {/* Live Calendar Subscription & Manual Export Card */}
            <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
              <CardHeader>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <CardTitle className="text-xl font-semibold flex items-center gap-2">
                      <svg className="w-5 h-5 fill-current text-indigo-400" viewBox="0 0 24 24">
                        <path d="M19 4h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V10h14v10zm0-12H5V6h14v2zm-7 5h5v5h-5z"/>
                      </svg>
                      <span>📅 Kalender & Kündigungsfristen (iCal / WebCal)</span>
                    </CardTitle>
                    <CardDescription className="mt-1">
                      Exportiere deine Kündigungsfristen in deinen Kalender (iPhone, Android, Google Kalender, Outlook).
                    </CardDescription>
                  </div>

                  <Button
                    type="button"
                    onClick={handleDownloadManualIcs}
                    className="theme-bg-accent text-white text-xs shrink-0 flex items-center gap-1.5"
                  >
                    📥 Alle Kündigungsfristen (.ics) herunterladen
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {webcalEnabled ? (
                  <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-800/50 space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <p className="text-xs font-mono text-indigo-300 font-bold uppercase tracking-wider">
                          Dein persönlicher WebCal-Live-Link
                        </p>
                        <p className="text-xs text-zinc-400 mt-0.5">
                          Dieser Link ist privat und synchronisiert deine Kündigungsfristen mit Vorwarnung (14 Tage & 7 Tage vorher) live.
                        </p>
                      </div>
                      {calendarTokenMsg && (
                        <span className="text-xs px-2.5 py-1 rounded bg-emerald-950 border border-emerald-800 text-emerald-300 font-mono shrink-0">
                          ✓ {calendarTokenMsg}
                        </span>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label className="text-xs font-mono text-zinc-400">WebCal / iCal URL</Label>
                      <div className="flex flex-col sm:flex-row gap-2">
                        <Input
                          readOnly
                          value={calendarToken ? `${typeof window !== "undefined" ? window.location.origin : "http://localhost:3000"}/api/users/calendar/feed.ics?token=${calendarToken}` : "Wird geladen..."}
                          className="bg-zinc-950 border-zinc-800 font-mono text-xs text-indigo-300 select-all"
                        />
                        <div className="flex gap-2 shrink-0">
                          <Button
                            type="button"
                            onClick={() => {
                              const link = `${typeof window !== "undefined" ? window.location.origin : "http://localhost:3000"}/api/users/calendar/feed.ics?token=${calendarToken}`;
                              const webcalLink = link.replace(/^https?:\/\//i, "webcal://");
                              navigator.clipboard.writeText(webcalLink);
                              alert("WebCal-Link in Zwischenablage kopiert!");
                            }}
                            className="theme-bg-accent text-white text-xs"
                          >
                            📋 Link kopieren
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => {
                              const link = `${typeof window !== "undefined" ? window.location.origin : "http://localhost:3000"}/api/users/calendar/feed.ics?token=${calendarToken}`;
                              const webcalLink = link.replace(/^https?:\/\//i, "webcal://");
                              window.location.href = webcalLink;
                            }}
                            className="border-indigo-700 bg-indigo-950/60 hover:bg-indigo-900 text-indigo-200 text-xs"
                          >
                            📱 In Kalender öffnen
                          </Button>
                        </div>
                      </div>
                    </div>

                    <div className="flex justify-between items-center pt-1 border-t border-indigo-900/40">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        disabled={calendarTokenLoading}
                        onClick={handleRotateCalendarToken}
                        className="text-xs text-zinc-400 hover:text-white p-0 h-auto font-mono"
                      >
                        🔄 Kalender-Token neu generieren (Sicherheitstoken zurücksetzen)
                      </Button>
                    </div>

                    {/* Instructions per OS */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 border-t border-indigo-900/40">
                      <div className="p-3.5 rounded-xl bg-zinc-950/60 border border-zinc-800 space-y-1.5">
                        <p className="text-xs font-bold text-zinc-200 flex items-center gap-1.5">
                          <span>🍎 iPhone / iPad / Mac</span>
                        </p>
                        <p className="text-[11px] text-zinc-400 leading-relaxed">
                          Klicke oben auf <strong>"In Kalender öffnen"</strong>. Apple Kalender öffnet sich und fragt nach Bestätigung.
                        </p>
                      </div>

                      <div className="p-3.5 rounded-xl bg-zinc-950/60 border border-zinc-800 space-y-1.5">
                        <p className="text-xs font-bold text-zinc-200 flex items-center gap-1.5">
                          <span>🤖 Android / Google</span>
                        </p>
                        <p className="text-[11px] text-zinc-400 leading-relaxed">
                          Öffne <a href="https://calendar.google.com" target="_blank" rel="noreferrer" className="text-indigo-400 underline font-semibold">calendar.google.com</a> ➔ <em>Weitere Kalender (+)</em> ➔ <em>Per URL hinzufügen</em>.
                        </p>
                      </div>

                      <div className="p-3.5 rounded-xl bg-zinc-950/60 border border-zinc-800 space-y-1.5">
                        <p className="text-xs font-bold text-zinc-200 flex items-center gap-1.5">
                          <span>💼 Outlook / Desktop</span>
                        </p>
                        <p className="text-[11px] text-zinc-400 leading-relaxed">
                          Wähle <strong>Kalender hinzufügen</strong> ➔ <em>Aus dem Internet abonnieren</em> ➔ Link einfügen.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800 space-y-2 text-xs text-zinc-400">
                    <p className="text-zinc-300 font-semibold flex items-center gap-2">
                      <span>ℹ️ WebCal Live-Sync ist aktuell deaktiviert</span>
                    </p>
                    <p className="leading-relaxed">
                      Der Administrator hat die automatische WebCal-Live-Synchronisation deaktiviert (z. B. bei rein lokaler Server-Nutzung ohne Nginx/Domain).
                      Du kannst deine Kündigungsfristen aber jederzeit über den Button oben als <strong>.ics-Datei herunterladen</strong> und in deinen Kalender importieren.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* System Settings Tab (Admin Only) */}
        {currentUser.is_admin && activeTab === "system" && (
          <div className="space-y-8">
            {/* 1-Click System Update Admin Settings Card */}
            <Card className="border-indigo-900/40 bg-zinc-900/50 backdrop-blur-md shadow-xl">
              <CardHeader>
                <CardTitle className="text-xl font-semibold flex items-center gap-2 text-white">
                  <RefreshCw className="w-5 h-5 text-zinc-400" />
                  <span>System-Update (1-Klick Aktualisierung)</span>
                </CardTitle>
                <CardDescription className="mt-1">
                  Aktualisiere Noxus Policy direkt per Klick aus dem Browser. Das System lädt den neuesten Stand von GitHub herunter, erstellt ein automatisches Sicherheits-Backup der Datenbank und baut die Container neu auf.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 rounded-xl bg-zinc-950/60 border border-zinc-800 gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-white">Installierte Version:</span>
                      <span className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-indigo-300 font-mono text-xs font-semibold">
                        {APP_VERSION}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-400">
                      Sichert automatisch die Datenbank unter <code className="text-zinc-300">/opt/versicherungsmanager/backups/</code> vor dem Update.
                    </p>
                  </div>

                  <Button
                    onClick={handleTriggerSystemUpdate}
                    disabled={isUpdating}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold flex items-center gap-2 px-5 py-2.5 rounded-lg shadow-lg transition-all cursor-pointer"
                  >
                    <RefreshCw className={`w-4 h-4 ${isUpdating ? 'animate-spin' : ''}`} />
                    <span>System-Update jetzt ausführen</span>
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* WebCal Live-Sync Admin Settings Card */}
            <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
              <CardHeader>
                <CardTitle className="text-xl font-semibold flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-zinc-400" />
                  <span>Live-Kalender-Abonnement (WebCal / iCal Sync)</span>
                </CardTitle>
                <CardDescription className="mt-1">
                  Aktiviere oder deaktiviere die Live-Synchronisation der Kündigungsfristen per WebCal-URL für deine Benutzer.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between p-4 rounded-xl bg-zinc-950/60 border border-zinc-800">
                  <div className="space-y-0.5">
                    <Label htmlFor="webcalEnabledToggle" className="text-sm font-semibold text-white cursor-pointer select-none">
                      WebCal Live-Abonnement für Benutzer freigeben
                    </Label>
                    <p className="text-xs text-zinc-400">
                      Erlaubt Benutzern das Erstellen eines privaten WebCal-Sync-Links für Smartphone-Kalender.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    id="webcalEnabledToggle"
                    checked={webcalEnabled}
                    disabled={webcalSaving}
                    onChange={e => handleSaveWebCalConfig(e.target.checked)}
                    className="w-5 h-5 rounded border-zinc-700 bg-zinc-900 text-indigo-600 focus:ring-indigo-500 accent-indigo-600 cursor-pointer shrink-0 ml-4"
                  />
                </div>

                {webcalMsg && (
                  <p className="text-xs font-mono text-emerald-400 bg-emerald-950/50 border border-emerald-800 p-2.5 rounded-lg">
                    ✓ {webcalMsg}
                  </p>
                )}

                {/* Important Server Accessibility Notice */}
                <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-800/50 text-amber-200 space-y-2 text-xs leading-relaxed">
                  <h4 className="font-bold text-amber-300 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                    <span>⚠️ Wichtiger Hinweis zur Server-Erreichbarkeit (Nginx / Domain):</span>
                  </h4>
                  <p className="text-zinc-300">
                    Das <strong>WebCal Live-Abonnement</strong> ermöglicht es externen Kalenderdiensten (z. B. <strong>Google Kalender Cloud, Apple iCloud, Outlook</strong>), Kündigungsfristen automatisch abzurufen.
                  </p>
                  <p className="text-zinc-300">
                    <strong>Voraussetzung:</strong> Diese Funktion erfordert, dass dieser Server <strong>von außen erreichbar ist</strong> (z. B. über einen <strong>Nginx Reverse Proxy</strong>, Cloudflare Tunnel oder eine öffentliche IP/Domain).
                  </p>
                  <p className="text-amber-300/90 font-mono text-[11px]">
                    💡 Wenn der Server rein lokal (z. B. <code>http://192.168.x.x:3000</code>) ohne externe Anbindung betrieben wird, können externe Kalender-Server nicht auf den Live-Link zugreifen. Deaktiviere in diesem Fall das WebCal-Live-Abonnement. Alle Benutzer können stattdessen weiterhin den <strong>manuellen .ics-Download</strong> nutzen!
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* AI OCR Engine Settings Card */}
            <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
              <CardHeader>
                <CardTitle className="text-xl font-semibold flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-zinc-400" />
                  <span>KI-gestützte Dokumentenanalyse & OCR Engine</span>
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
                  <Clock className="w-5 h-5 text-zinc-400" />
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

                  <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center pt-2 border-t border-zinc-800/80 gap-3 w-full">
                    <Button
                      type="button"
                      variant="outline"
                      disabled={autoBackupRunning}
                      onClick={handleRunBackupNow}
                      className="border-indigo-800 bg-indigo-950/50 hover:bg-indigo-900 text-indigo-300 text-xs w-full sm:w-auto"
                    >
                      {autoBackupRunning ? "Erstelle Backup..." : "⚡ Sofort Backup auf Server erstellen"}
                    </Button>

                    <Button type="submit" disabled={autoBackupSaving} className="theme-bg-accent text-white theme-glow text-xs font-medium w-full sm:w-auto">
                      {autoBackupSaving ? "Speichert..." : "Zeitplan & Regeln speichern"}
                    </Button>
                  </div>
                </form>

                {/* Stored Server Backups Table */}
                <div className="pt-6 border-t border-zinc-800/80 space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <Database className="w-4 h-4 text-zinc-400" />
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
                  <Database className="w-5 h-5 text-zinc-400" />
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
                      <Database className="w-4 h-4 text-zinc-400" />
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
                      <Database className="w-4 h-4 text-zinc-400" />
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
                    <Mail className="w-5 h-5 text-zinc-400" />
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

                  <div className="flex flex-col sm:flex-row sm:justify-between items-stretch sm:items-center pt-2 border-t border-zinc-800/80 gap-3 w-full">
                    <Button
                      type="button"
                      variant="outline"
                      disabled={smtpTesting}
                      onClick={handleSmtpTest}
                      className="border-indigo-800 bg-indigo-950/50 hover:bg-indigo-900 text-indigo-300 text-xs w-full sm:w-auto"
                    >
                      {smtpTesting ? "Testet..." : "Test-E-Mail senden"}
                    </Button>

                    <Button type="submit" disabled={smtpSaving} className="theme-bg-accent text-white theme-glow text-xs font-medium w-full sm:w-auto">
                      {smtpSaving ? "Speichert..." : "SMTP-Einstellungen speichern"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>

            {/* Admin User Management Section */}
            <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
              <CardHeader>
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 w-full">
                  <div>
                    <CardTitle className="text-xl font-semibold flex items-center gap-2">
                      <Users className="w-5 h-5 text-zinc-400" />
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
                    className="border-indigo-800 bg-indigo-950/50 text-indigo-300 text-xs hover:bg-indigo-900 w-full sm:w-auto shrink-0"
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

      {/* System Update Progress Modal */}
      {showUpdateModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-indigo-900/60 rounded-2xl p-6 sm:p-8 max-w-md w-full text-center space-y-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
            {updateSuccess ? (
              <div className="flex justify-center">
                <div className="w-16 h-16 rounded-full bg-emerald-950/80 border border-emerald-500/50 flex items-center justify-center text-emerald-400 animate-bounce">
                  <CheckCircle2 className="w-10 h-10" />
                </div>
              </div>
            ) : updateError ? (
              <div className="flex justify-center">
                <div className="w-16 h-16 rounded-full bg-red-950/80 border border-red-500/50 flex items-center justify-center text-red-400">
                  <AlertCircle className="w-10 h-10" />
                </div>
              </div>
            ) : (
              <div className="flex justify-center">
                <div className="w-16 h-16 rounded-full bg-indigo-950/80 border border-indigo-500/50 flex items-center justify-center text-indigo-400">
                  <Loader2 className="w-10 h-10 animate-spin" />
                </div>
              </div>
            )}

            <div className="space-y-2">
              <h3 className="text-xl font-bold text-white">
                {updateSuccess ? "System-Update erfolgreich!" : updateError ? "Fehler beim Update" : "System-Update wird durchgeführt..."}
              </h3>
              <p className="text-sm text-zinc-300 leading-relaxed">
                {updateStatusMsg}
              </p>
            </div>

            {updateError && (
              <div className="p-3 rounded-lg bg-red-950/50 border border-red-800/60 text-red-300 text-xs font-mono text-left max-h-32 overflow-y-auto">
                {updateError}
              </div>
            )}

            {updateError && (
              <Button
                onClick={() => setShowUpdateModal(false)}
                className="w-full bg-zinc-800 hover:bg-zinc-700 text-white font-medium py-2 rounded-lg"
              >
                Schließen
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
