import type { Activity, County, Difficulty } from "../types/trail";

const ALL_ACTIVITIES: Activity[] = [
  "hiking",
  "biking",
  "horseback",
  "xc_ski",
  "snowshoe",
];

const ALL_COUNTIES: County[] = [
  "marathon",
  "lincoln",
  "langlade",
  "taylor",
  "shawano",
  "portage",
];

const ALL_DIFFICULTIES: Difficulty[] = [
  "easy",
  "moderate",
  "difficult",
  "strenuous",
];

const COUNTY_LABELS: Record<County, string> = {
  marathon: "Marathon",
  lincoln: "Lincoln",
  langlade: "Langlade",
  taylor: "Taylor",
  shawano: "Shawano",
  portage: "Portage",
};

const ACTIVITY_LABELS: Record<Activity, string> = {
  hiking: "Hiking",
  biking: "Biking",
  horseback: "Horseback",
  xc_ski: "XC ski",
  snowshoe: "Snowshoe",
  snowmobile: "Snowmobile",
};

const DIFFICULTY_LABELS: Record<Difficulty, string> = {
  easy: "Easy",
  moderate: "Moderate",
  difficult: "Difficult",
  strenuous: "Strenuous",
};

export interface FilterState {
  activities: Set<Activity>;
  counties: Set<County>;
  difficulties: Set<Difficulty>;
  /** Max drive minutes from Wausau; null = no limit */
  maxDriveMin: number | null;
  /** Length range in miles [min, max] */
  lengthMi: [number, number];
}

export const LENGTH_MAX_MI = 80;

interface Props {
  state: FilterState;
  onChange: (next: FilterState) => void;
  trailCount: number;
  totalCount: number;
}

export default function FilterBar({
  state,
  onChange,
  trailCount,
  totalCount,
}: Props) {
  const toggle = <T,>(set: Set<T>, value: T): Set<T> => {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    return next;
  };

  return (
    <aside className="w-72 shrink-0 overflow-y-auto border-r border-gray-200 bg-white p-4">
      <h1 className="text-lg font-semibold text-gray-900">WPR Trails</h1>
      <p className="mt-1 text-xs text-gray-500">
        Hiking conditions in north-central Wisconsin
      </p>

      <ChipSection title="Activity">
        {ALL_ACTIVITIES.map((a) => (
          <Chip
            key={a}
            label={ACTIVITY_LABELS[a]}
            active={state.activities.has(a)}
            onClick={() => onChange({ ...state, activities: toggle(state.activities, a) })}
          />
        ))}
      </ChipSection>

      <ChipSection title="County">
        {ALL_COUNTIES.map((c) => (
          <Chip
            key={c}
            label={COUNTY_LABELS[c]}
            active={state.counties.has(c)}
            onClick={() => onChange({ ...state, counties: toggle(state.counties, c) })}
          />
        ))}
      </ChipSection>

      <ChipSection title="Difficulty">
        {ALL_DIFFICULTIES.map((d) => (
          <Chip
            key={d}
            label={DIFFICULTY_LABELS[d]}
            active={state.difficulties.has(d)}
            onClick={() => onChange({ ...state, difficulties: toggle(state.difficulties, d) })}
          />
        ))}
      </ChipSection>

      <SliderSection
        title="Max drive from Wausau"
        value={state.maxDriveMin ?? 120}
        min={15}
        max={120}
        step={15}
        unit="min"
        unsetLabel="No limit"
        unset={state.maxDriveMin === null}
        onChange={(v) => onChange({ ...state, maxDriveMin: v })}
      />

      <RangeSection
        title="Length"
        value={state.lengthMi}
        min={0}
        max={LENGTH_MAX_MI}
        step={1}
        unit="mi"
        onChange={(v) => onChange({ ...state, lengthMi: v })}
      />

      <div className="mt-6 text-xs text-gray-500">
        Showing {trailCount} of {totalCount} trails
      </div>
    </aside>
  );
}

function ChipSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-5">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
        {title}
      </h2>
      <div className="mt-2 flex flex-wrap gap-1.5">{children}</div>
    </div>
  );
}

function Chip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "rounded-full border px-3 py-1 text-xs transition " +
        (active
          ? "border-emerald-600 bg-emerald-600 text-white"
          : "border-gray-300 bg-white text-gray-700 hover:border-gray-400")
      }
    >
      {label}
    </button>
  );
}

function SliderSection({
  title,
  value,
  min,
  max,
  step,
  unit,
  unsetLabel,
  unset,
  onChange,
}: {
  title: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  unsetLabel: string;
  unset: boolean;
  onChange: (v: number | null) => void;
}) {
  return (
    <div className="mt-5">
      <div className="flex items-baseline justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          {title}
        </h2>
        <span className="text-xs tabular-nums text-gray-700">
          {unset ? unsetLabel : `≤ ${value} ${unit}`}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => {
          const v = Number(e.target.value);
          onChange(v >= max ? null : v);
        }}
        className="mt-2 w-full accent-emerald-600"
      />
    </div>
  );
}

function RangeSection({
  title,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  title: string;
  value: [number, number];
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (v: [number, number]) => void;
}) {
  const [lo, hi] = value;
  return (
    <div className="mt-5">
      <div className="flex items-baseline justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          {title}
        </h2>
        <span className="text-xs tabular-nums text-gray-700">
          {lo}–{hi} {unit}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={lo}
          onChange={(e) => {
            const v = Math.min(Number(e.target.value), hi);
            onChange([v, hi]);
          }}
          className="w-1/2 accent-emerald-600"
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={hi}
          onChange={(e) => {
            const v = Math.max(Number(e.target.value), lo);
            onChange([lo, v]);
          }}
          className="w-1/2 accent-emerald-600"
        />
      </div>
    </div>
  );
}
