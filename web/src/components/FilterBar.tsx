import type { Activity, County } from "../types/trail";

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

interface Props {
  activities: Set<Activity>;
  counties: Set<County>;
  onToggleActivity: (a: Activity) => void;
  onToggleCounty: (c: County) => void;
  trailCount: number;
  totalCount: number;
}

export default function FilterBar({
  activities,
  counties,
  onToggleActivity,
  onToggleCounty,
  trailCount,
  totalCount,
}: Props) {
  return (
    <aside className="w-72 shrink-0 overflow-y-auto border-r border-gray-200 bg-white p-4">
      <h1 className="text-lg font-semibold text-gray-900">WPR Trails</h1>
      <p className="mt-1 text-xs text-gray-500">
        Hiking conditions in north-central Wisconsin
      </p>

      <Section title="Activity">
        {ALL_ACTIVITIES.map((a) => (
          <Chip
            key={a}
            label={ACTIVITY_LABELS[a]}
            active={activities.has(a)}
            onClick={() => onToggleActivity(a)}
          />
        ))}
      </Section>

      <Section title="County">
        {ALL_COUNTIES.map((c) => (
          <Chip
            key={c}
            label={COUNTY_LABELS[c]}
            active={counties.has(c)}
            onClick={() => onToggleCounty(c)}
          />
        ))}
      </Section>

      <div className="mt-6 text-xs text-gray-500">
        Showing {trailCount} of {totalCount} trails
      </div>
    </aside>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
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
