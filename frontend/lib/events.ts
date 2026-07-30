export function buildEventHref(event: string | null | undefined, eventYear?: number | null) {
  if (!event) {
    return null;
  }
  const base = `/events/${encodeURIComponent(event)}`;
  if (eventYear == null) {
    return base;
  }
  return `${base}?year=${eventYear}`;
}
