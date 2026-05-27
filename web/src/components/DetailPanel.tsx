import type { RankedTrail, Trail } from "../types/trail";

type TrailState =
  | { status: "idle" }
  | { status: "loading"; id: string }
  | { status: "ready"; trail: Trail }
  | { status: "error"; id: string; message: string };

interface Props {
  trailId: string;
  trailState: TrailState;
  ranked: RankedTrail | undefined;
  onClose: () => void;
}

const FACTOR_LABELS: Record<string, string> = {
  mud_risk: "Mud risk",
  daylight: "Daylight",
  exposure: "Exposure",
  seasonality: "Seasonality",
  scenery_match: "Scenery match",
  freshness: "Freshness",
};

export default function DetailPanel({ trailId, trailState, ranked, onClose }: Props) {
  return (
    <aside
      className={
        "absolute z-[1000] flex flex-col border-gray-200 bg-white shadow-lg " +
        // Desktop: right-anchored full-height drawer
        "sm:right-0 sm:top-0 sm:h-full sm:w-96 sm:border-l sm:rounded-none " +
        // Mobile: bottom-anchored sheet, max ~75% viewport height
        "inset-x-0 bottom-0 max-h-[75vh] rounded-t-xl border-t"
      }
    >
      <header className="flex items-start justify-between gap-2 border-b border-gray-200 p-4">
        <div className="min-w-0">
          {trailState.status === "ready" ? (
            <h2 className="truncate text-base font-semibold text-gray-900">
              {trailState.trail.name}
            </h2>
          ) : (
            <h2 className="truncate text-base font-semibold text-gray-400">
              {ranked?.name ?? trailId}
            </h2>
          )}
          {ranked && (
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-2xl font-semibold text-emerald-700">
                {ranked.score.toFixed(0)}
              </span>
              <span className="text-xs text-gray-500">/ 100 today</span>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-900"
        >
          ✕
        </button>
      </header>

      <div className="flex-1 overflow-y-auto p-4">
        {trailState.status === "loading" && (
          <div className="text-sm text-gray-500">Loading trail…</div>
        )}
        {trailState.status === "error" && (
          <div className="text-sm text-red-600">Failed to load: {trailState.message}</div>
        )}
        {trailState.status === "ready" && (
          <TrailBody trail={trailState.trail} ranked={ranked} />
        )}
      </div>
    </aside>
  );
}

function TrailBody({
  trail,
  ranked,
}: {
  trail: Trail;
  ranked: RankedTrail | undefined;
}) {
  const a = trail.attributes;
  const d = trail.derived;
  const lengthMi = (a.length_m / 1609.34).toFixed(1);
  const gainFt = Math.round(a.elevation_gain_m * 3.2808);

  return (
    <>
      <Section title="At a glance">
        <Stat label="Length" value={`${lengthMi} mi`} />
        <Stat label="Elevation gain" value={`${gainFt} ft`} />
        <Stat label="Difficulty" value={titleCase(a.difficulty_estimated)} />
        <Stat label="Loop" value={a.is_loop ? "Yes" : "Out & back"} />
        <Stat
          label="Drive from Wausau"
          value={`${d.drive_minutes_from_wausau} min`}
        />
        {a.managing_authority && (
          <Stat label="Managed by" value={a.managing_authority} />
        )}
        {a.blaze_color && (
          <Stat label="Blaze" value={titleCase(a.blaze_color)} />
        )}
        {a.surface.length > 0 && (
          <Stat label="Surface" value={a.surface.map(titleCase).join(", ")} />
        )}
        <Stat
          label="Counties"
          value={a.counties.map(titleCase).join(", ")}
        />
        {d.trailhead_coords && (
          <div className="border-b border-gray-100 py-1.5 text-sm last:border-b-0">
            <div className="flex justify-between">
              <span className="text-gray-500">Trailhead</span>
              <a
                href={`https://www.google.com/maps/dir/?api=1&destination=${d.trailhead_coords[1]},${d.trailhead_coords[0]}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-right text-emerald-700 hover:underline"
              >
                Directions →
              </a>
            </div>
            {d.parking_distance_m !== null && d.parking_distance_m !== undefined && (
              <div className="mt-0.5 text-right text-xs text-gray-400">
                {d.parking_distance_m}m to nearest parking
              </div>
            )}
          </div>
        )}
      </Section>

      {ranked && (
        <Section title="Why this score">
          <ul className="space-y-2">
            {[...ranked.factors]
              .sort((x, y) => y.weight - x.weight)
              .map((f) => (
                <li key={f.name}>
                  <div className="flex items-baseline justify-between text-sm">
                    <span className="font-medium text-gray-900">
                      {FACTOR_LABELS[f.name] ?? f.name}
                    </span>
                    <span className="tabular-nums text-xs text-gray-500">
                      {(f.value * 100).toFixed(0)} ·{" "}
                      {(f.weight * 100).toFixed(0)}% weight
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
                    <div
                      className="h-full bg-emerald-500"
                      style={{ width: `${f.value * 100}%` }}
                    />
                  </div>
                  <div className="mt-1 text-xs text-gray-500">{f.note}</div>
                </li>
              ))}
          </ul>
        </Section>
      )}
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-6">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        {title}
      </h3>
      {children}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-gray-100 py-1.5 text-sm last:border-b-0">
      <span className="text-gray-500">{label}</span>
      <span className="text-right text-gray-900">{value}</span>
    </div>
  );
}

function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
