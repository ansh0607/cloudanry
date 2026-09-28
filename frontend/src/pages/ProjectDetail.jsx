import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import RelevanceBadge from "../components/RelevanceBadge";
import UploadWidget from "../components/UploadWidget";

export default function ProjectDetail() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [gallery, setGallery] = useState(null);
  const [groupBy, setGroupBy] = useState("date");
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api(`/api/projects/${id}`).then(setProject).catch((e) => setError(e.message));
  }, [id]);

  useEffect(() => {
    setGallery(null);
    api(`/api/media?project_id=${id}&group_by=${groupBy}`)
      .then(setGallery)
      .catch((e) => setError(e.message));
  }, [id, groupBy]);

  async function runSearch(e) {
    e.preventDefault();
    if (!query.trim()) return setSearchResults(null);
    try {
      const data = await api(`/api/search?q=${encodeURIComponent(query)}&project_id=${id}`);
      setSearchResults(data.results);
    } catch (err) {
      setError(err.message);
    }
  }

  const items = searchResults
    ? [{ key: `search: ${query}`, count: searchResults.length, items: searchResults }]
    : gallery?.groups || [];

  return (
    <div className="space-y-6">
      {project && (
        <div>
          <h2 className="text-xl font-semibold text-slate-800">{project.project_name}</h2>
          <p className="text-sm text-slate-500">{project.description}</p>
          <p className="mt-1 text-xs text-slate-400">
            {project.location?.place_name || "no location"} · {project.expected_activity_type || "no activity type"}
          </p>
          <nav className="mt-3 flex flex-wrap gap-2 text-sm">
            <span className="rounded-full bg-emerald-600 px-3 py-1 font-medium text-white">Gallery</span>
            <Link to={`/projects/${id}/compare`} className="rounded-full border border-slate-300 px-3 py-1 text-slate-600 hover:border-emerald-400">
              Before / after
            </Link>
            <Link to={`/projects/${id}/claims`} className="rounded-full border border-slate-300 px-3 py-1 text-slate-600 hover:border-emerald-400">
              Claims
            </Link>
            <a
              href={`${import.meta.env.VITE_API_BASE || "http://localhost:8000"}/api/projects/${id}/report`}
              target="_blank"
              rel="noreferrer"
              className="rounded-full border border-slate-300 px-3 py-1 text-slate-600 hover:border-emerald-400"
            >
              📄 Report ↗
            </a>
          </nav>
        </div>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="mb-2 font-semibold text-slate-800">Upload evidence</h3>
        <UploadWidget projectId={id} onUploaded={() => setGallery(null)} />
      </section>

      <form onSubmit={runSearch} className="flex gap-2">
        <input
          placeholder="Search media by tag or description…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full max-w-md rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        />
        <button className="rounded-md bg-slate-700 px-4 py-1.5 text-sm font-medium text-white hover:bg-slate-800">
          Search
        </button>
        {searchResults && (
          <button
            type="button"
            onClick={() => { setSearchResults(null); setQuery(""); }}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          >
            Clear
          </button>
        )}
      </form>

      <div className="flex items-center gap-2">
        <span className="text-sm text-slate-500">Group by:</span>
        {["date", "location"].map((g) => (
          <button
            key={g}
            onClick={() => { setGroupBy(g); setSearchResults(null); }}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              groupBy === g ? "bg-emerald-600 text-white" : "border border-slate-300 text-slate-600"
            }`}
          >
            {g}
          </button>
        ))}
        <span className="ml-2 text-xs text-slate-400">{gallery?.total ?? 0} items</span>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {items.map((group) => (
        <section key={group.key}>
          <h3 className="mb-2 text-sm font-semibold text-slate-600">
            {group.key} <span className="font-normal text-slate-400">({group.count})</span>
          </h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {group.items.map((m) => (
              <Link
                key={m.id}
                to={`/media/${m.id}`}
                className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm hover:shadow"
              >
                <div className="relative h-32 w-full bg-slate-100">
                  {m.thumbnail_url || m.cloudinary_url ? (
                    <img
                      src={m.thumbnail_url || m.cloudinary_url}
                      alt=""
                      className="h-full w-full object-cover"
                      onError={(e) => (e.target.style.display = "none")}
                    />
                  ) : null}
                  {m.media_type === "video" && (
                    <span className="absolute right-1 top-1 rounded bg-black/60 px-1 text-[10px] text-white">
                      video
                    </span>
                  )}
                  {m.duplicate_matches?.length > 0 && (
                    <span className="absolute left-1 top-1 rounded bg-red-600 px-1 text-[10px] text-white">
                      duplicate
                    </span>
                  )}
                </div>
                <div className="p-2">
                  <RelevanceBadge score={m.relevance_score} />
                  <p className="mt-1 line-clamp-2 text-[11px] text-slate-500">
                    {m.image_description || m.relevance_reasoning || "no description"}
                  </p>
                  <p className="mt-1 text-[10px] text-slate-400">
                    {(m.capture_date || "unknown date").slice(0, 10)}
                    {m.ai_tags?.length ? ` · ${m.ai_tags.slice(0, 3).join(", ")}` : ""}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
