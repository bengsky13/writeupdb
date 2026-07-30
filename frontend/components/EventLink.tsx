import Link from "next/link";

import { buildEventHref } from "../lib/events";

export function EventLink({
  event,
  eventYear,
  className = "label",
}: {
  event?: string | null;
  eventYear?: number | null;
  className?: string;
}) {
  if (!event) {
    return <span className={className}>Unknown event</span>;
  }

  const href = buildEventHref(event, eventYear);
  if (!href) {
    return <span className={className}>{eventYear ? `${event} ${eventYear}` : event}</span>;
  }

  return (
    <Link href={href} className={`${className} eventLink`}>
      {eventYear ? `${event} ${eventYear}` : event}
    </Link>
  );
}
