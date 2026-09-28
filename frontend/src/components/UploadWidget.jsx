import { useState } from "react";
import { api, API_BASE } from "../api";

export default function UploadWidget({ projectId, onUploaded }) {
  const [file, setFile] = useState(null);
  const [useLocation, setUseLocation] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function getLocation() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) return resolve(null);
      navigator.geolocation.getCurrentPosition(
        (pos) =>
          resolve(
            JSON.stringify({
              lat: Number(pos.coords.latitude.toFixed(6)),
              lng: Number(pos.coords.longitude.toFixed(6)),
            })
          ),
        () => resolve(null),
        { timeout: 5000 }
      );
    });
  }

  async function submit(e) {
    e.preventDefault();
    if (!file) return setError("Choose a photo or video first");
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("project_id", projectId);
      fd.append("file", file);
      if (useLocation) {
        const gps = await getLocation();
        if (gps) fd.append("gps", gps);
      }
      const data = await api("/api/media/upload", { method: "POST", body: fd });
      setResult(data);
      setFile(null);
      e.target.reset?.();
      onUploaded?.(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <form onSubmit={submit} className="flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept="image/*,video/*"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="text-sm file:mr-3 file:rounded-md file:border-0 file:bg-emerald-600 file:px-3 file:py-1.5 file:text-white"
        />
        <label className="flex items-center gap-1 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={useLocation}
            onChange={(e) => setUseLocation(e.target.checked)}
          />
          attach device GPS
        </label>
        <button
          disabled={busy}
          className="rounded-md bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          {busy ? "Uploading + analyzing…" : "Upload"}
        </button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {result && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm">
          <p className="font-medium">Uploaded and analyzed</p>
          <p className="text-slate-600">
            relevance {result.relevance_score ?? "n/a"} · type {result.media_type}
            {result.gps ? ` · gps ${result.gps.lat}, ${result.gps.lng}` : " · no gps"}
          </p>
          {result.relevance_reasoning && (
            <p className="mt-1 text-slate-500">{result.relevance_reasoning}</p>
          )}
          {result.duplicate_matches?.length > 0 && (
            <p className="mt-1 font-medium text-red-700">
              ⚠ {result.duplicate_matches.length} near-duplicate(s) detected
            </p>
          )}
          <img
            src={result.thumbnail_url || result.cloudinary_url}
            alt=""
            className="mt-2 h-28 rounded-md object-cover"
          />
        </div>
      )}
    </div>
  );
}
