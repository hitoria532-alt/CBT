import { useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import AdminLayout from "./components/AdminLayout";
import StudentLayout from "./components/StudentLayout";
import Dashboard from "./pages/admin/Dashboard";
import Categories from "./pages/admin/Categories";
import Questions from "./pages/admin/Questions";
import Packages from "./pages/admin/Packages";
import Sessions from "./pages/admin/Sessions";
import Classes from "./pages/admin/Classes";
import Results from "./pages/admin/Results";
import Accounts from "./pages/admin/Accounts";
import StudentHome from "./pages/student/StudentHome";
import ExamView from "./pages/student/ExamView";
import StudentResults from "./pages/student/StudentResults";
import ResultDetail from "./pages/student/ResultDetail";

function Loader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
    </div>
  );
}

function Protected({ children, roles }) {
  const { user } = useAuth();
  if (user === null) return <Loader />;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role))
    return <Navigate to={user.role === "siswa" ? "/" : "/admin"} replace />;
  return children;
}

function Root() {
  const { user } = useAuth();
  if (user === null) return <Loader />;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "siswa" ? "/beranda" : "/admin"} replace />;
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <Toaster position="top-right" richColors />
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Root />} />

            {/* Admin / Guru */}
            <Route
              path="/admin"
              element={
                <Protected roles={["admin", "guru"]}>
                  <AdminLayout />
                </Protected>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="kategori" element={<Categories />} />
              <Route path="soal" element={<Questions />} />
              <Route path="paket" element={<Packages />} />
              <Route path="sesi" element={<Sessions />} />
              <Route path="kelas" element={<Classes />} />
              <Route path="hasil" element={<Results />} />
              <Route path="akun" element={<Accounts />} />
            </Route>

            {/* Student */}
            <Route
              element={
                <Protected roles={["siswa"]}>
                  <StudentLayout />
                </Protected>
              }
            >
              <Route path="/beranda" element={<StudentHome />} />
              <Route path="/hasil" element={<StudentResults />} />
              <Route path="/hasil/:attemptId" element={<ResultDetail />} />
            </Route>

            <Route
              path="/ujian/:sessionId"
              element={
                <Protected roles={["siswa"]}>
                  <ExamView />
                </Protected>
              }
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
