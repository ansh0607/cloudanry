import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";

function scoreColor(score) {
  if (score === null || score === undefined) return "text-slate-400";
  if (score > 80) return "text-green-600";
  if (score >= 60) return "text-amber-500";
  return "text-red-600";
}

function ClaimCard({ claim }) {
  const [open, setOpen] = useState(false);
  const dupSignals = (claim.adversarial_signals || []).filter((s) => s.duplicate_media_id);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-medium text-slate-800">{claim.claim_text}</p>
          <p className="mt-1 text-xs text-slate-400">
            {claim.linked_media_ids?.length || 0} linked media ·{" "}
            {(claim.created_at || "").slice(0, 10)}
          </p>
        </div>
        <div className="text-right">
          <p className={`text-4xl font-bold ${scoreColor(claim.confidence_score)}`}>
            {claim.confidence_score ?? "—"}
          </p>
          <p className="text-[11px] text-slate-400">confidence (assessment)</p>
        </div>
      </div>

      {dupSignals.length > 0 && (
        <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm">
          <p className="font-semibold text-red-700">Contradiction trace</p>
          <ul className="mt-1 list-disc pl-5 text-red-700">
            {dupSignals.map((s, i) => (
              <li key={i}>
                photo {s.basis === "deterministic_phash_check" ? "reused" : "flagged"} → similar to
                media <span className="font-mono text-xs">{s.duplicate_media_id}</span>
                {s.similarity ? ` (${s.similarity}%)` : ""} → flagged as near-duplicate
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        onClick={() => setOpen(!open)}
        className="mt-3 text-sm font-medium text-emerald-700 hover:underline"
      >
        {open ? "Hide breakdown" : "Show signal breakdown"}
      </button>

      {open && (
        <div className="mt-2 space-y-3 border-t border-slate-100 pt-3">
          {(claim.score_breakdown || []).map((b, i) => (
            <div key={i} className="flex items-start justify-between gap-3 text-sm">
              <div>
                <span
                  className={`mr-2 inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                    b.step === "supporting"
                      ? "bg-green-100 text-green-800"
                      : b.step === "adversarial"
                        ? "bg-red-100 text-red-800"
                        : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {b.step}
                </span>
                <span className="text-slate-700">{b.description}</span>
              </div>
              <span className={`font-mono text-xs ${b.delta >= 0 ? "text-green-700" : "text-red-700"}`}>
                {b.delta >= 0 ? "+" : ""}{b.delta}
              </span>
            </div>
          ))}
          <div className="grid gap-2 sm:grid-cols-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-green-700">Supporting signals</p>
              <ul className="list-disc pl-5 text-sm text-slate-600">
                {(claim.supporting_signals || []).map((s, i) => (
                  <li key={i}>
                    {s.description} <em className="text-xs">(strength {s.strength})</em>
                  </li>
                )) || null}
                {(claim.supporting_signals || []).length === 0 && <li className="list-none text-slate-400">none</li>}
              </ul>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-red-700">Adversarial signals</p>
              <ul className="list-disc pl-5 text-sm text-slate-600">
                {(claim.adversarial_signals || []).map((s, i) => (
                  <li key={i}>
                    {s.description} <em className="text-xs">(severity {s.severity})</em>
                  </li>
                ))}
                {(claim.adversarial_signals || []).length === 0 && <li className="list-none text-slate-400">none</li>}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Claims() {
  const { id } = useParams();
  const [claims, setClaims] = useState([]);
  const [media, setMedia] = useState([]);
  const [claimText, setClaimText] = useState("");
  const [selected, setSelected] = useState(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api(`/api/claims?project_id=${id}`).then(setClaims).catch((e) => setError(e.message));
    api(`/api/media?project_id=${id}&group_by=date`)
      .then((g) => setMedia(g.groups.flatMap((grp) => grp.items)))
      .catch(() => {});
  }, [id]);

  function toggle(mediaId) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(mediaId) ? next.delete(mediaId) : next.add(mediaId);
      return next;
    });
  }

  async function createClaim(e) {
    e.preventDefault();
    if (!claimText.trim() || selected.size === 0)
      return setError("Write a claim and select at least one media item");
    setBusy(true);
    setError(null);
    try {
      await api("/api/claims", {
        method: "POST",
        body: JSON.stringify({
          project_id: id,
          claim_text: claimText,
          linked_media_ids: [...selected],
        }),
      });
      setClaimText("");
      setSelected(new Set());
      api(`/api/claims?project_id=${id}`).then(setClaims).catch(() => {});
    } catch (err) {
      setError(err.message);
    }finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_360px]">
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-slate-800">Claims &amp; confidence</h2>
        {claims.length === 0 && (
          <p className="text-sm text-slate-500">No claims yet — create one on the right.</p>
        )}
        {claims.map((c) => (
          <ClaimCard key={c.id} claim={c} />
        ))}
      </div>

      <form onSubmit={createClaim} className="h-fit space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="font-semibold text-slate-800">New claim</h3>
        <textarea
          placeholder="e.g. Tree cover increased at the restoration site between March and August"
          value={claimText}
          onChange={(e) => setClaimText(e.target.value)}
          rows={3}
          className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        />
        <p className="text-xs text-slate-500">Select linked media ({selected.size} selected):</p>
        <div className="max-h-64 space-y-1 overflow-y-auto">
          {media.map((m) => (
            <label key={m.id} className="flex items-center gap-2 rounded-md p-1 text-xs hover:bg-slate-50">
              <input type="checkbox" checked={selected.has(m.id)} onChange={() => toggle(m.id)} />
              <img src={m.thumbnail_url || m.cloudinary_url} alt="" className="h-8 w-12 rounded object-cover" />
              <span className="text-slate-600">{(m.capture_date || "unknown").slice(0, 10)}</span>
              {m.duplicate_matches?.length > 0 && <span className="text-red-600">⚠ dup</span>}
            </label>
          ))}
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          disabled={busy}
          className="w-full rounded-md bg-emerald-600 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          {busy ? "Analyzing (dual AI)…" : "Analyze claim"}
        </button>
        <p className="text-[11px] text-slate-400">
          Supporting AI and Adversarial AI run in parallel on different models; the confidence
          score is a deterministic weighted calculation, not an AI opinion.
        </p>
      </form>
    </div>
  );
}
