import { useState } from "react";

/**
 * Inline email contact panel. Clicking the trigger reveals the address with
 * a Copy button + a mailto link. Designed to work even when the user has no
 * default mail handler — in that case copy + paste into webmail.
 *
 * Ported from wpr-river-conditions/src/components/EmailCTA.jsx for visual
 * parity across WPR widgets.
 */
interface Props {
  triggerLabel: string;
  triggerClassName?: string;
  email: string;
  subject: string;
  body: string;
}

export default function EmailCTA({
  triggerLabel,
  triggerClassName = "",
  email,
  subject,
  body,
}: Props) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const mailto = `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

  const handleTrigger = (e: React.MouseEvent) => {
    e.preventDefault();
    setOpen(true);
    setCopied(false);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(email);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // execCommand fallback for older / restricted browsers
      const el = document.createElement("textarea");
      el.value = email;
      document.body.appendChild(el);
      el.select();
      try {
        document.execCommand("copy");
        setCopied(true);
      } catch {
        /* swallow */
      }
      document.body.removeChild(el);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!open) {
    return (
      <a
        href={mailto}
        target="_blank"
        rel="noopener noreferrer"
        className={triggerClassName}
        onClick={handleTrigger}
      >
        {triggerLabel}
      </a>
    );
  }

  return (
    <div className="email-cta">
      <div className="email-cta__row">
        <span className="email-cta__label">Email:</span>
        <code className="email-cta__address">{email}</code>
        <button
          type="button"
          className="email-cta__btn email-cta__btn--copy"
          onClick={handleCopy}
        >
          {copied ? "Copied ✓" : "Copy"}
        </button>
      </div>
      <div className="email-cta__actions">
        <a
          className="email-cta__btn email-cta__btn--open"
          href={mailto}
          target="_blank"
          rel="noopener noreferrer"
        >
          Open in email app
        </a>
        <button
          type="button"
          className="email-cta__btn email-cta__btn--close"
          onClick={() => setOpen(false)}
        >
          Close
        </button>
      </div>
      <div className="email-cta__hint">
        If "Open in email app" doesn't work, copy the address and use your
        preferred email service. Suggested subject: <em>{subject}</em>
      </div>
    </div>
  );
}
