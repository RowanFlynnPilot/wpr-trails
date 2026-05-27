import type { Activity, County, Difficulty, SceneryTag } from "../types/trail";
import { DIFFICULTY_COLORS } from "./TrailPin";

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

const ALL_SCENERY: SceneryTag[] = [
  "water",
  "wetland",
  "overlook",
  "prairie",
  "rocky_outcrop",
  "old_growth",
  "glacial",
];

const SCENERY_LABELS: Record<SceneryTag, string> = {
  water: "Water",
  wetland: "Wetland",
  overlook: "Overlook",
  prairie: "Prairie",
  rocky_outcrop: "Rocky outcrop",
  old_growth: "Old growth",
  glacial: "Glacial",
};

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
  search: string;
  activities: Set<Activity>;
  counties: Set<County>;
  difficulties: Set<Difficulty>;
  scenery: Set<SceneryTag>;
  familyOnly: boolean;
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
  open: boolean;
  onClose: () => void;
}

export default function FilterBar({
  state,
  onChange,
  trailCount,
  totalCount,
  open,
  onClose,
}: Props) {
  const toggle = <T,>(set: Set<T>, value: T): Set<T> => {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    return next;
  };

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-[1099] bg-black/40 sm:hidden"
          aria-hidden
        />
      )}
      <aside
        className={
          "z-[1100] flex flex-col overflow-y-auto border-gray-200 bg-white p-4 transition-transform sm:relative sm:z-auto sm:w-72 sm:shrink-0 sm:translate-x-0 sm:border-r " +
          "fixed inset-y-0 left-0 w-80 border-r shadow-xl sm:shadow-none " +
          (open ? "translate-x-0" : "-translate-x-full sm:translate-x-0")
        }
      >
      <div className="flex items-center justify-between sm:hidden">
        <h2 className="font-display text-base font-bold text-wpr-ink">Filters</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close filters"
          className="rounded p-1 text-wpr-ink-muted hover:bg-wpr-cream"
        >
          ✕
        </button>
      </div>

      <div className="mt-1 sm:mt-0">
        <input
          type="search"
          value={state.search}
          onChange={(e) => onChange({ ...state, search: e.target.value })}
          placeholder="Search trail name…"
          className="w-full rounded-md border border-wpr-rule bg-white px-3 py-1.5 font-body text-sm placeholder:text-wpr-ink-muted focus:border-wpr-teal focus:outline-none focus:ring-1 focus:ring-wpr-teal"
        />
      </div>

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
            swatch={DIFFICULTY_COLORS[d]}
          />
        ))}
      </ChipSection>

      <ChipSection title="Scenery">
        {ALL_SCENERY.map((s) => (
          <Chip
            key={s}
            label={SCENERY_LABELS[s]}
            active={state.scenery.has(s)}
            onClick={() => onChange({ ...state, scenery: toggle(state.scenery, s) })}
          />
        ))}
      </ChipSection>

      <div className="mt-5">
        <ToggleRow
          label="Family-friendly only"
          checked={state.familyOnly}
          onChange={(v) => onChange({ ...state, familyOnly: v })}
        />
      </div>

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
    </>
  );
}

function ToggleRow({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between rounded px-2 py-1 text-sm hover:bg-gray-50">
      <span className="text-gray-700">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-gray-300 text-wpr-teal focus:ring-wpr-teal"
      />
    </label>
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
  swatch,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  swatch?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition " +
        (active
          ? "border-wpr-teal bg-wpr-teal text-white"
          : "border-gray-300 bg-white text-gray-700 hover:border-gray-400")
      }
    >
      {swatch && (
        <span
          className="inline-block h-2 w-2 rounded-full"
          style={{ backgroundColor: swatch }}
          aria-hidden
        />
      )}
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
        className="mt-2 w-full accent-wpr-teal"
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
          className="w-1/2 accent-wpr-teal"
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
          className="w-1/2 accent-wpr-teal"
        />
      </div>
    </div>
  );
}
