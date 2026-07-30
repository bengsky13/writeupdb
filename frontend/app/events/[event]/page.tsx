import Link from "next/link";
import { notFound } from "next/navigation";

import { BackButton } from "../../../components/BackButton";
import { EventLink } from "../../../components/EventLink";
import { Nav } from "../../../components/Nav";
import { Pagination } from "../../../components/Pagination";
import { fetchJson } from "../../../lib/api";

type EventWriteup = {
  id: number;
  title: string;
  event?: string | null;
  event_year?: number | null;
  challenge?: string | null;
  category?: string | null;
  team?: string | null;
  published_at?: string | null;
};

type EventResponse = {
  event: string;
  event_year?: number | null;
  items: EventWriteup[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export default async function EventPage({
  params,
  searchParams,
}: {
  params: Promise<{ event: string }>;
  searchParams: Promise<{ page?: string; year?: string }>;
}) {
  const { event } = await params;
  const eventName = decodeURIComponent(event);
  const query = await searchParams;
  const page = Math.max(Number(query.page ?? "1") || 1, 1);
  const year = query.year ? Number(query.year) : null;
  const yearParam = year ? `&event_year=${year}` : "";

  let data: EventResponse;
  try {
    data = await fetchJson<EventResponse>(
      `/api/events/${encodeURIComponent(eventName)}?page=${page}&limit=20${yearParam}`,
    );
  } catch {
    notFound();
  }

  const pageBase = `/events/${encodeURIComponent(eventName)}`;
  const pageQueryPrefix = year ? `${pageBase}?year=${year}&page=` : `${pageBase}?page=`;

  return (
    <main className="shell grid">
      <Nav />
      <section className="card grid">
        <div className="searchRow">
          <BackButton fallbackHref="/" />
        </div>
        <div className="label">Event</div>
        <h1 className="sectionTitle">{year ? `${data.event} ${year}` : data.event}</h1>
        <div className="muted">{data.total} writeups in the local collection.</div>
      </section>
      <section className="grid">
        {data.items.length === 0 ? (
          <div className="card muted">No writeups found for this event.</div>
        ) : (
          data.items.map((writeup) => (
            <article key={writeup.id} className="card result">
              <EventLink event={writeup.event} eventYear={writeup.event_year} />
              <Link href={`/writeups/${writeup.id}`}>
                <h2>{writeup.title}</h2>
              </Link>
              <div className="chips">
                {writeup.challenge ? <span className="chip">{writeup.challenge}</span> : null}
                {writeup.category ? <span className="chip">{writeup.category}</span> : null}
                {writeup.team ? <span className="chip">{writeup.team}</span> : null}
              </div>
              <div className="muted">
                {writeup.published_at
                  ? `Published ${new Date(writeup.published_at).toLocaleDateString("en-CA")}`
                  : "Publication date unavailable"}
              </div>
            </article>
          ))
        )}
        <Pagination page={data.page} totalPages={data.total_pages} makeHref={(nextPage) => `${pageQueryPrefix}${nextPage}`} />
      </section>
    </main>
  );
}
