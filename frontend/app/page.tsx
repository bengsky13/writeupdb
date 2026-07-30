import Link from "next/link";

import { EventLink } from "../components/EventLink";
import { Nav } from "../components/Nav";
import { Pagination } from "../components/Pagination";
import { SearchForm } from "../components/SearchForm";
import { fetchJson } from "../lib/api";

const examples = [
  "glibc 2.35 safe linking tcache poisoning",
  "\"malloc(): unaligned tcache chunk detected\"",
  "Flask session cookie forgery",
  "PNG data hidden after IEND"
];

type HomeWriteup = {
  id: number;
  title: string;
  event?: string | null;
  event_year?: number | null;
  challenge?: string | null;
  category?: string | null;
  team?: string | null;
  published_at?: string | null;
};

type PaginatedResponse<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const params = await searchParams;
  const page = Math.max(Number(params.page ?? "1") || 1, 1);
  const newestWriteups = await fetchJson<PaginatedResponse<HomeWriteup>>(`/api/writeups?page=${page}&limit=20`);

  return (
    <main className="shell grid">
      <Nav />
      <section className="hero">
        <span className="label">Offline CTF Writeup Search</span>
        <h1>Search prose, payloads, code, and exploitation steps without the internet.</h1>
        <p>
          The collection stays local. Ingestion comes from a feeding agent, batch imports, watched packages,
          or manual admin uploads. Search blends lexical, metadata, exact phrase, and semantic retrieval.
        </p>
        <SearchForm />
        <div className="chips">
          {examples.map((example) => (
            <Link key={example} href={`/search?q=${encodeURIComponent(example)}`} className="chip">
              {example}
            </Link>
          ))}
        </div>
      </section>
      <section className="grid stats">
        <div className="card"><div className="label">Index Mode</div><div className="value">Hybrid</div></div>
        <div className="card"><div className="label">Runtime</div><div className="value">Fully Offline</div></div>
        <div className="card"><div className="label">Ingestion</div><div className="value">API + Packages</div></div>
        <div className="card"><div className="label">Storage</div><div className="value">Local PostgreSQL</div></div>
      </section>
      <section className="grid">
        <div className="sectionHead">
          <div>
            <div className="label">Newest Writeups</div>
            <h2 className="sectionTitle">Latest indexed writeups</h2>
          </div>
        </div>
        <div className="grid">
          {newestWriteups.items.length === 0 ? (
            <div className="card muted">No writeups ingested yet.</div>
          ) : (
            newestWriteups.items.map((writeup) => (
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
                  {writeup.published_at ? `Published ${new Date(writeup.published_at).toLocaleDateString("en-CA")}` : "Publication date unavailable"}
                </div>
              </article>
            ))
          )}
        </div>
        <Pagination page={newestWriteups.page} totalPages={newestWriteups.total_pages} makeHref={(page) => `/?page=${page}`} />
      </section>
    </main>
  );
}
