import Link from "next/link";

import { BackButton } from "../../components/BackButton";
import { EventLink } from "../../components/EventLink";
import { Nav } from "../../components/Nav";
import { Pagination } from "../../components/Pagination";
import { SearchForm } from "../../components/SearchForm";
import { fetchJson } from "../../lib/api";

type SearchResponse = {
  latency_ms: number;
  results: Array<{
    id: number;
    title: string;
    event?: string | null;
    event_year?: number | null;
    challenge?: string | null;
    category?: string | null;
    matched_section?: string | null;
    highlight: string;
    score: number;
    explanation: Record<string, unknown>;
    attachments: Array<{ filename: string; type?: string | null }>;
  }>;
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export default async function SearchPage({
  searchParams
}: {
  searchParams: Promise<{ q?: string; page?: string }>;
}) {
  const params = await searchParams;
  const query = params.q ?? "";
  const page = Math.max(Number(params.page ?? "1") || 1, 1);
  const data = query
    ? await fetchJson<SearchResponse>(`/api/search?q=${encodeURIComponent(query)}&page=${page}&limit=20&debug=true`)
    : null;

  return (
    <main className="shell grid">
      <Nav />
      <div className="card grid">
        <div className="searchRow">
          <BackButton fallbackHref="/" />
        </div>
        <SearchForm initialQuery={query} />
        <div className="muted">
          {data ? `Latency ${data.latency_ms} ms • ${data.total} results` : "Enter a query to search the local collection."}
        </div>
      </div>
      <div className="grid">
        {data?.results.map((result) => (
          <article key={result.id} className="card result">
            <EventLink event={result.event} eventYear={result.event_year} />
            <Link href={`/writeups/${result.id}`}><h2>{result.title}</h2></Link>
            <div className="chips">
              {result.challenge ? <span className="chip">{result.challenge}</span> : null}
              {result.category ? <span className="chip">{result.category}</span> : null}
              {result.matched_section ? <span className="chip">{result.matched_section}</span> : null}
              <span className="chip">score {result.score}</span>
            </div>
            <p>{result.highlight}</p>
            <div className="muted">Attachments: {result.attachments.map((item) => item.filename).join(", ") || "none"}</div>
            <div className="muted">Explanation: {JSON.stringify(result.explanation)}</div>
          </article>
        ))}
      </div>
      {data ? (
        <Pagination
          page={data.page}
          totalPages={data.total_pages}
          makeHref={(nextPage) => `/search?q=${encodeURIComponent(query)}&page=${nextPage}`}
        />
      ) : null}
    </main>
  );
}
