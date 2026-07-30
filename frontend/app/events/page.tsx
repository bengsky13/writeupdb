import Link from "next/link";

import { BackButton } from "../../components/BackButton";
import { Nav } from "../../components/Nav";
import { Pagination } from "../../components/Pagination";
import { fetchJson } from "../../lib/api";
import { buildEventHref } from "../../lib/events";

type EventItem = {
  event: string;
  event_year?: number | null;
  writeup_count: number;
  latest_writeup_at?: string | null;
};

type EventListResponse = {
  items: EventItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export default async function EventsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const params = await searchParams;
  const page = Math.max(Number(params.page ?? "1") || 1, 1);
  const data = await fetchJson<EventListResponse>(`/api/events?page=${page}&limit=20`);

  return (
    <main className="shell grid">
      <Nav />
      <section className="card grid">
        <div className="searchRow">
          <BackButton fallbackHref="/" />
        </div>
        <div className="label">Events</div>
        <h1 className="sectionTitle">All events</h1>
        <div className="muted">{data.total} event entries in the local collection.</div>
      </section>
      <section className="grid">
        {data.items.length === 0 ? (
          <div className="card muted">No events available yet.</div>
        ) : (
          data.items.map((item) => {
            const href = buildEventHref(item.event, item.event_year) ?? "/events";
            return (
              <article key={`${item.event}-${item.event_year ?? "na"}`} className="card result">
                <Link href={href}>
                  <h2>{item.event_year ? `${item.event} ${item.event_year}` : item.event}</h2>
                </Link>
                <div className="chips">
                  <span className="chip">{item.writeup_count} writeups</span>
                </div>
                <div className="muted">
                  {item.latest_writeup_at
                    ? `Latest indexed ${new Date(item.latest_writeup_at).toLocaleDateString("en-CA")}`
                    : "No indexed timestamp"}
                </div>
              </article>
            );
          })
        )}
        <Pagination page={data.page} totalPages={data.total_pages} makeHref={(nextPage) => `/events?page=${nextPage}`} />
      </section>
    </main>
  );
}
