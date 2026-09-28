import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import DisclaimerBanner from "./components/DisclaimerBanner";
import Claims from "./pages/Claims";
import ComparePage from "./pages/ComparePage";
import Dashboard from "./pages/Dashboard";
import MediaDetail from "./pages/MediaDetail";
import ProjectDetail from "./pages/ProjectDetail";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50">
        <DisclaimerBanner />
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
            <Link to="/" className="text-lg font-bold text-emerald-700">
              🌿 Evidence Graph
            </Link>
            <nav className="text-sm text-slate-500">
              <Link to="/" className="hover:text-emerald-700">Projects</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/projects/:id/compare" element={<ComparePage />} />
            <Route path="/projects/:id/claims" element={<Claims />} />
            <Route path="/media/:id" element={<MediaDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
