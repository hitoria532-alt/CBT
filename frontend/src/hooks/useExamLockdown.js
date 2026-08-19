import { useCallback, useEffect, useRef, useState } from "react";
import api from "../lib/api";

/**
 * "Mode Ujian Ketat" (exam lockdown) for the student exam screen.
 *
 * A web page can NOT lock a phone at OS level — only a native app with kiosk /
 * screen-pinning can do that. What this hook does is the strongest thing a
 * browser allows:
 *   - forces fullscreen (works on Android Chrome; iOS Safari has no fullscreen API)
 *   - keeps the screen awake while the exam runs
 *   - detects leaving the exam: tab hidden, window blur, fullscreen exit
 *   - blocks copy/paste/context-menu and the usual devtools / new-tab shortcuts
 *   - reports every violation to the server, which auto-submits at the limit
 */
export default function useExamLockdown({ active, sessionId, maxViolations, initialCount, onAutoSubmit }) {
  const [count, setCount] = useState(initialCount || 0);
  const [blocked, setBlocked] = useState(false);
  const [lastReason, setLastReason] = useState("");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const busy = useRef(false);
  const stopped = useRef(false);
  const wakeLock = useRef(null);

  const enterFullscreen = useCallback(async () => {
    const el = document.documentElement;
    try {
      if (!document.fullscreenElement && el.requestFullscreen) {
        await el.requestFullscreen({ navigationUI: "hide" });
      } else if (!document.webkitFullscreenElement && el.webkitRequestFullscreen) {
        await el.webkitRequestFullscreen();
      }
    } catch {
      /* iOS Safari & some in-app browsers refuse fullscreen — detection still works */
    }
    try {
      if ("wakeLock" in navigator && !wakeLock.current) {
        wakeLock.current = await navigator.wakeLock.request("screen");
      }
    } catch { /* wake lock unsupported */ }
    try {
      if (window.screen?.orientation?.lock) await window.screen.orientation.lock("portrait");
    } catch { /* orientation lock unsupported */ }
  }, []);

  const releaseLocks = useCallback(() => {
    stopped.current = true;
    try { wakeLock.current?.release?.(); } catch { /* noop */ }
    wakeLock.current = null;
    try {
      if (document.fullscreenElement && document.exitFullscreen) document.exitFullscreen();
    } catch { /* noop */ }
  }, []);

  const report = useCallback(async (type, reason) => {
    if (!active || stopped.current || busy.current) return;
    busy.current = true;
    setBlocked(true);
    setLastReason(reason);
    try {
      const { data } = await api.post("/exam/violation", { session_id: sessionId, type });
      setCount(data.count);
      if (data.auto_submitted) {
        stopped.current = true;
        releaseLocks();
        onAutoSubmit?.(data.count);
      }
    } catch {
      setCount((c) => c + 1); // still warn the student if the report fails
    } finally {
      busy.current = false;
    }
  }, [active, sessionId, onAutoSubmit, releaseLocks]);

  const resume = useCallback(async () => {
    setBlocked(false);
    await enterFullscreen();
  }, [enterFullscreen]);

  useEffect(() => {
    if (!active) return undefined;
    stopped.current = false;

    const onVisibility = () => {
      if (document.hidden) report("tab_hidden", "Anda meninggalkan halaman ujian (pindah tab atau menutup aplikasi).");
    };
    const onBlur = () => {
      if (!document.hidden) report("window_blur", "Jendela ujian kehilangan fokus.");
    };
    const onFsChange = () => {
      const fs = Boolean(document.fullscreenElement || document.webkitFullscreenElement);
      setIsFullscreen(fs);
      if (!fs && !stopped.current) report("fullscreen_exit", "Anda keluar dari mode layar penuh.");
    };
    const onContext = (e) => e.preventDefault();
    const onCopy = (e) => {
      e.preventDefault();
      report("copy_attempt", "Menyalin atau menempel teks tidak diizinkan selama ujian.");
    };
    const onKeyDown = (e) => {
      const k = (e.key || "").toLowerCase();
      const blockedCombo =
        k === "f12" ||
        ((e.ctrlKey || e.metaKey) && e.shiftKey && ["i", "j", "c"].includes(k)) ||
        ((e.ctrlKey || e.metaKey) && ["t", "n", "w", "p", "s", "u", "o"].includes(k)) ||
        (e.altKey && k === "tab");
      if (blockedCombo) {
        e.preventDefault();
        e.stopPropagation();
        report("shortcut_blocked", "Tombol pintas tersebut tidak diizinkan selama ujian.");
      }
    };
    const onBeforeUnload = (e) => { e.preventDefault(); e.returnValue = ""; return ""; };

    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("blur", onBlur);
    document.addEventListener("fullscreenchange", onFsChange);
    document.addEventListener("webkitfullscreenchange", onFsChange);
    document.addEventListener("contextmenu", onContext);
    document.addEventListener("copy", onCopy);
    document.addEventListener("cut", onCopy);
    document.addEventListener("paste", onCopy);
    document.addEventListener("keydown", onKeyDown, true);
    window.addEventListener("beforeunload", onBeforeUnload);
    document.body.classList.add("exam-locked");

    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("blur", onBlur);
      document.removeEventListener("fullscreenchange", onFsChange);
      document.removeEventListener("webkitfullscreenchange", onFsChange);
      document.removeEventListener("contextmenu", onContext);
      document.removeEventListener("copy", onCopy);
      document.removeEventListener("cut", onCopy);
      document.removeEventListener("paste", onCopy);
      document.removeEventListener("keydown", onKeyDown, true);
      window.removeEventListener("beforeunload", onBeforeUnload);
      document.body.classList.remove("exam-locked");
    };
  }, [active, report]);

  return {
    count, max: maxViolations, blocked, lastReason, isFullscreen,
    enterFullscreen, releaseLocks, resume,
  };
}
