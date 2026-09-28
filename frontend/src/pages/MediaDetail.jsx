import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import RelevanceBadge from "../components/RelevanceBadge";

export default function MediaDetail() {
  const { id } = useParams();
  const [media, setMedia] = useState(null);
  const [audit, setAudit] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api(`/api/media/${id}`).then(setMedia).catch((e) => setError(e.message));
    api(`/api/media/${id}/audit`).then(setAudit).catch(() => {});
  }, [id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!media) return <p className="text-sm text-slate-500">Loading…</p>;

  const gps = media.gps || null;

  return (
    <div className="space-y-6">
      <Link to={media.project_id ? `/projects/${media.project_id}` : "/"} className="text-sm text-emerald-700 hover:underline">
        ← back to project
      </Link>

      <div className="grid gap-6 md:grid-cols-[380px_1fr]">
        <div>
          {media.media_type === "video" && media.cloudinary_url ? (
            <video src={media.cloudinary_url} controls className="w-full rounded-xl border border-slate-200 shadow-sm" />
          ) : (
            <img
              src={media.cloudinary_url}
              alt=""
              className="w-full rounded-xl border border-slate-200 shadow-sm"
              onError={(e) => (e.target.style.display = "none")}
            />
          )}
          <a
            href={media.cloudinary_url}
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-block text-xs text-slate-400 hover:text-emerald-700"
          >
            original source asset ↗
          </a>
        </div>

        <div className="space-y-4">
          <div>
            <RelevanceBadge score={media.relevance_score} />
            {media.image_description && (
              <p className="mt-2 text-sm text-slate-700">{media.image_description}</p>
            )}
            {media.relevance_reasoning && (
              <p className="mt-1 text-xs text-slate-500">Why: {media.relevance_reasoning}</p>
            )}
            <p className="mt-1 text-xs text-slate-400">
              location match: {String(media.location_match ?? "unclear")} · content match:{" "}
              {String(media.content_match ?? "unclear")}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2 text-sm text-slate-600">
            <p><span className="text-slate-400">Type:</span> {media.media_type}</p>
            <p><span className="text-slate-400">Captured:</span> {(media.capture_date || "unknown").slice(0, 19)}</p>
            <p>
              <span className="text-slate-400">GPS:</span>{" "}
              {gps ? `${gps.lat}, ${gps.lng}` : "none"}
            </p>
            <p><span className="text-slate-400">phash:</span> <span className="font-mono text-xs">{media.phash || "—"}</span></p>
          </div>

          {media.ai_tags?.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">AI tags</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {media.ai_tags.map((t) => (
                  <span key={t} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{t}</span>
                ))}
              </div>
            </div>
          )}
          {media.cloudinary_tags?.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Cloudinary auto-tags</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {media.cloudinary_tags.map((t) => (
                  <span key={t} className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">{t}</span>
                ))}
              </div>
            </div>
          )}

          {media.duplicate_matches?.length > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm">
              <p className="font-semibold text-red-700">⚠ Near-duplicate detected</p>
              <ul className="mt-1 list-disc pl-5 text-red-700">
                {media.duplicate_matches.map((d, i) => (
                  <li key={i}>
                    <Link to={`/media/${d.media_id}`} className="underline">
                      media {d.media_id.slice(0, 8)}
                    </Link>{" "}
                    — {d.similarity_percent}% similar
                    {d.project_id ? ` (project ${d.project_id.slice(0, 8)})` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <h3 className="mb-2 font-semibold text-slate-800">Audit trail</h3>
            <ol className="space-y-2 border-l-2 border-emerald-200 pl-4">
              {audit.length === 0 && <li className="text-sm text-slate-400">No audit entries found.</li>}
              {audit.map((a) => (
                <li key={a.id} className="text-sm">
                  <span className="font-medium text-slate-700">{a.action}</span>{" "}
                  <span className="text-xs text-slate-400">{(a.timestamp || "").slice(0, 19).replace("T", " ")}</span>
                  {a.after_state?.relevance_score !== undefined && a.after_state?.relevance_score !== null && (
                    <span className="text-xs text-slate-500"> · relevance {a.after_state.relevance_score}</span>
                  )}
                  {a.after_state?.duplicate_matches?.length > 0 && (
                    <span className="text-xs text-red-600"> · {a.after_state.duplicate_matches.length} duplicate flag(s)</span>
                  )}
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
