interface Props {
  /** ISO timestamp of when the displayed data was last refreshed. */
  updatedAt: string | null;
  /** Called when the mobile hamburger button is tapped. */
  onMenuClick: () => void;
}

export default function ChromeBar({ updatedAt, onMenuClick }: Props) {
  return (
    <header className="chrome-bar">
      <div className="chrome-bar__left">
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="Open filters"
          className="chrome-bar__menu-btn"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
            <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </button>
        <a
          className="chrome-bar__brand"
          href="https://wausaupilotandreview.com"
          target="_blank"
          rel="noopener noreferrer"
        >
          <img
            className="chrome-bar__logo-img"
            src={`${import.meta.env.BASE_URL}logo-32.png`}
            alt="Wausau Pilot & Review"
          />
          <span className="chrome-bar__logo">Wausau Pilot &amp; Review</span>
          <span className="chrome-bar__divider" />
          <span className="chrome-bar__section-name">Trail Conditions</span>
        </a>
      </div>
      {updatedAt && (
        <span className="chrome-bar__updated">{formatUpdatedAt(updatedAt)}</span>
      )}
    </header>
  );
}

function formatUpdatedAt(iso: string): string {
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMin = Math.floor((now.getTime() - d.getTime()) / 60000);

    if (diffMin < 1) return "Just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;

    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}
