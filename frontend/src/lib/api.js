import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const api = axios.create({ baseURL: API, withCredentials: true });

api.interceptors.request.use((config) => {
  const t = localStorage.getItem("token");
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

export function apiError(e) {
  const detail = e?.response?.data?.detail;
  if (detail == null) return e?.message || "Terjadi kesalahan.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((x) => (x && x.msg ? x.msg : JSON.stringify(x))).join(" ");
  if (detail && detail.msg) return detail.msg;
  return String(detail);
}

export const fileUrl = (path) =>
  path ? `${API}/files/${path}?auth=${encodeURIComponent(localStorage.getItem("token") || "")}` : null;

export { API };
export default api;
