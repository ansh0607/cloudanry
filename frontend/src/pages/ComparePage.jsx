import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";

export default function ComparePage() {
  const { id } = useParams();
  const [media, setMedia] = useState([]);
  const [aId, setAId] = useState("");
  const [bId, setBId] = useState("");
  const [result, setResult] = useState(null);
  const [slider, setSlider] = useState(50);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api(`/api/media?project_id=${id}&group_by=date`)
      .then((g) => setMedia(g.groups.flatMap((grp) => grp.items)))
      .catch((e) => setError(e.message));
  }, [id]);

  async function runCompare(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const data = await api("/api/compare", {
        method: "POST",
        body: JSON.stringify({ media_id_a: aId, media_id_b: bId }),
      });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const delta = result?.green_ratio_delta_percent ?? null;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-800">Before / after</h2>
      <form onSubmit={runCompare} className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <select value={aId} onChange={(e) => setAId(e.target.value)} className="rounded-md border border-slate-300 px-2 py-1.5 text-sm">
          <option value="">Before…</option>
          {media.map((m) => (
            <option key={m.id} value={m.id}>
              {(m.capture_date || "unknown").slice(0, 10)} — {m.id.slice(0, 6)}
            </option>
          ))}
        </select>
        <select value={bId} onChange={(e) => setBId(e.target.value)} className="rounded-md border border-slate-300 px-2 py-1.5 text-sm">
          <option value="">After…</option>
          {media.map((m) => (
            <option key={m.id} value={m.id}>
              {(m.capture_date || "unknown").slice(0, 10)} — {m.id.slice(0, 6)}
            </option>
          ))}
        </select>
        <button
          disabled={!aId || !bId || busy || aId === bId}
          className="rounded-md bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          {busy ? "Comparing…" : "Compare"}
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {result && (
        <div className="space-y-4">
          <div className="relative h-96 w-full max-w-3xl select-none overflow-hidden rounded-xl border border-slate-200 shadow-sm">
            <img src={result.media_a.cloudinary_url} alt="before" className="absolute inset-0 h-full w-full object-cover" />
            <div className="absolute inset-0 overflow-hidden" style={{ width: `${slider}%` }}>
              <img src={result.media_b.cloudinary_url} alt="after" className="h-full w-full object-cover" style={{ width: `${10000 / slider}%`, maxWidth: "none" }} />
            </div>
            <div className="absolute inset-y-0 border-l-2 border-white" style={{ left: `${slider}%` }} />
            <input
              type="range"
              min={0}
              max={100}
              value={slider}
              onChange={(e) => setSlider(Number(e.target.value))}
              className="absolute inset-x-0 bottom-3 mx-auto w-[95%] accent-emerald-600"
            />
            <span className="absolute left-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white">
              after · {(result.capture_date_b || "").slice(0, 10)}
            </span>
            <span className="absolute right-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white">
              before · {(result.capture_date_a || "").slice(0, 10)}
            </span>
          </div>

          <div className="grid max-w-3xl gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase tracking-wide text-slate-400">Green ratio (vegetation proxy)</p>
              <p className="text-2xl font-bold text-slate-800">
                {result.green_ratio_a} → {result.green_ratio_b}
              </p>
              <p className={`text-sm font-medium ${delta >= 0 ? "text-green-700" : "text-red-700"}`}>
                {delta >= 0 ? "+" : ""}{delta} pp
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase tracking-wide text-slate-400">Overall pixel change</p>
              <p className="text-2xl font-bold text-slate-800">{result.pixel_diff_percent}%</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 text-xs text-slate-500 shadow-sm">
              Simple color-threshold metrics computed locally in &lt;2s. Change is
              &ldquo;consistent with&rdquo; project activity — it does not by itself prove cause.
            </div>
            <input type="hidden" value={result.chronological_order} />
          </div>
        </div>
      )}
    </div>
  );
}
