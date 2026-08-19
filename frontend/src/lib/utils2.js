export function fmtDateTime(iso) {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString("id-ID", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function toLocalInput(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const off = d.getTimezoneOffset();
  const local = new Date(d.getTime() - off * 60000);
  return local.toISOString().slice(0, 16);
}

export function fromLocalInput(v) {
  if (!v) return "";
  return new Date(v).toISOString();
}

export const STATUS_LABEL = {
  akan_datang: "Akan Datang",
  berlangsung: "Berlangsung",
  selesai: "Selesai",
  menunggu_koreksi: "Menunggu Koreksi",
};

export const ROLE_LABEL = { admin: "Admin", guru: "Guru", siswa: "Siswa" };
export const QTYPE_LABEL = { pg: "Pilihan Ganda", truefalse: "Benar / Salah", essay: "Esai" };

export const POLICY_LABEL = {
  tertinggi: "Nilai tertinggi",
  terakhir: "Nilai percobaan terakhir",
  rata: "Rata-rata semua percobaan",
};

/**
 * Radix leaves `pointer-events: none` on <body> when a Dialog unmounts while a
 * Select/Popover inside it was still open, which makes the page feel frozen.
 * Call this whenever a dialog is closed programmatically.
 */
export function releaseBodyPointerEvents() {
  requestAnimationFrame(() => {
    if (document.body.style.pointerEvents === "none") {
      document.body.style.pointerEvents = "";
    }
    document.querySelectorAll("[data-radix-popper-content-wrapper]").forEach((el) => el.remove());
  });
}
