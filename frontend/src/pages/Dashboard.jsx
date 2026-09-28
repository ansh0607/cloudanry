import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    project_name: "",
    description: "",
    place_name: "",
    lat: "",
    lng: "",
    expected_activity_type: "",
  });

  useEffect(() => {
    api("/api/projects").then(setProjects).catch((e) => setError(e.message));
  }, []);

  async function createProject(e) {
    e.preventDefault();
    setError(null);
    try {
      const loc =
        form.place_name || form.lat || form.lng
          ? {
              place_name: form.place_name || null,
              lat: form.lat ? Number(form.lat) : null,
              lng: form.lng ? Number(form.lng) : null,
            }
          : null;
      const created = await api("/api/projects", {
        method: "POST",
        body: JSON.stringify({
          project_name: form.project_name,
          description: form.description,
          location: loc,
          expected_activity_type: form.expected_activity_type || null,
        }),
      });
      setProjects([created, ...projects]);
      setForm({ project_name: "", description: "", place_name: "", lat: "", lng: "", expected_activity_type: "" });
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_320px]">
      <div>
        <h2 className="mb-3 text-lg font-semibold text-slate-800">Projects</h2>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {projects.length === 0 && !error && (
          <p className="text-sm text-slate-500">No projects yet — create one on the right.</p>
        )}
        <div className="grid gap-3 sm:grid-cols-2">
          {projects.map((p) => (
            <Link
              key={p.id}
              to={`/projects/${p.id}`}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-emerald-300 hover:shadow"
            >
              <h3 className="font-semibold text-slate-800">{p.project_name}</h3>
              <p className="mt-1 line-clamp-2 text-sm text-slate-500">{p.description}</p>
              <p className="mt-2 text-xs text-slate-400">
                {p.location?.place_name || (p.location?.lat ? `${p.location.lat}, ${p.location.lng}` : "no location")}
                {p.expected_activity_type ? ` · ${p.expected_activity_type}` : ""}
              </p>
            </Link>
          ))}
        </div>
      </div>

      <form
        onSubmit={createProject}
        className="h-fit space-y-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
      >
        <h3 className="font-semibold text-slate-800">New project</h3>
        <input
          required
          placeholder="Project name"
          value={form.project_name}
          onChange={(e) => setForm({ ...form, project_name: e.target.value })}
          className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        />
        <textarea
          placeholder="Description (what should the media show?)"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          rows={3}
        />
        <input
          placeholder="Place name"
          value={form.place_name}
          onChange={(e) => setForm({ ...form, place_name: e.target.value })}
          className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        />
        <div className="flex gap-2">
          <input
            placeholder="lat"
            value={form.lat}
            onChange={(e) => setForm({ ...form, lat: e.target.value })}
            className="w-1/2 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          />
          <input
            placeholder="lng"
            value={form.lng}
            onChange={(e) => setForm({ ...form, lng: e.target.value })}
            className="w-1/2 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          />
        </div>
        <input
          placeholder="Expected activity (e.g. tree planting)"
          value={form.expected_activity_type}
          onChange={(e) => setForm({ ...form, expected_activity_type: e.target.value })}
          className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        />
        <button className="w-full rounded-md bg-emerald-600 py-1.5 text-sm font-medium text-white hover:bg-emerald-700">
          Create project
        </button>
      </form>
    </div>
  );
}
