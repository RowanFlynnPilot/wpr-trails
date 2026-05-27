import type { ConditionsSummary } from "../types/trail";

interface Props {
  conditions: ConditionsSummary;
  alertCount: number;
  computedAt: string;
}

export default function WeatherBanner({ conditions, alertCount, computedAt }: Props) {
  const c = conditions;
  const precip = c.recent_precip_in_72h;
  const wet = precip !== null && precip >= 0.5;

  return (
    <div className="pointer-events-none absolute right-3 top-3 z-[400] flex max-w-[60vw] flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-gray-200 bg-white/95 px-3 py-2 text-xs shadow-sm backdrop-blur sm:left-4 sm:right-auto sm:top-4 sm:max-w-md sm:gap-x-4">
      {c.forecast_temp_f !== null && (
        <Stat label="Temp" value={`${Math.round(c.forecast_temp_f)}°F`} />
      )}
      {c.forecast_wind_mph !== null && (
        <Stat label="Wind" value={`${Math.round(c.forecast_wind_mph)} mph`} />
      )}
      {c.forecast_precip_chance !== null && (
        <Stat label="Rain" value={`${c.forecast_precip_chance}%`} />
      )}
      {precip !== null && (
        <Stat
          label="72h precip"
          value={`${precip.toFixed(1)}″`}
          tone={wet ? "warn" : "neutral"}
        />
      )}
      {alertCount > 0 && (
        <Stat label="Alerts" value={String(alertCount)} tone="warn" />
      )}
      <span className="text-[10px] text-gray-400">
        as of {formatTime(computedAt)}
      </span>
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "warn";
}) {
  return (
    <span className="flex items-baseline gap-1">
      <span className="text-gray-500">{label}</span>
      <span
        className={
          tone === "warn"
            ? "font-semibold text-amber-700"
            : "font-semibold text-gray-900"
        }
      >
        {value}
      </span>
    </span>
  );
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      hour: "numeric",
      minute: "2-digit",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}
