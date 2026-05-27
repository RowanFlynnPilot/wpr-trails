import EmailCTA from "./EmailCTA";

const INQUIRY_EMAIL = "rowan.flynn@wausaupilotandreview.com";
const INQUIRY_SUBJECT = "Sponsorship inquiry: Trail Conditions widget";
const INQUIRY_BODY = `Hi Rowan,

I'd like to learn more about sponsoring the trail conditions widget on Wausau Pilot & Review.

Thanks,`;

/**
 * Bottom-of-page sponsor CTA. Currently always shows the "Reach out" prompt
 * since there's no active sponsor for the trails widget. When a sponsor lands,
 * port the river-conditions sponsor.json pattern and switch on a `sponsor`
 * prop.
 */
export default function SponsorStrip() {
  return (
    <div className="sponsor-strip sponsor-strip--cta">
      Interested in sponsoring this content?{" "}
      <EmailCTA
        triggerLabel="Reach out →"
        triggerClassName="sponsor-strip__cta-link"
        email={INQUIRY_EMAIL}
        subject={INQUIRY_SUBJECT}
        body={INQUIRY_BODY}
      />
    </div>
  );
}
