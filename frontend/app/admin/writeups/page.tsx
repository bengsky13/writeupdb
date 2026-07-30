import Link from "next/link";

import { AdminNav } from "../../../components/AdminNav";
import { BackButton } from "../../../components/BackButton";
import { DeleteWriteupButton } from "../../../components/DeleteWriteupButton";
import { Nav } from "../../../components/Nav";
import { Pagination } from "../../../components/Pagination";
import { fetchJson } from "../../../lib/api";

type AdminWriteup = {
  id: number;
  title: string;
  external_id: string;
  event?: string | null;
  challenge?: string | null;
  category?: string | null;
  team?: string | null;
};

type PaginatedResponse<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export default async function AdminWriteupsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const params = await searchParams;
  const page = Math.max(Number(params.page ?? "1") || 1, 1);
  const writeups = await fetchJson<PaginatedResponse<AdminWriteup>>(`/api/admin/writeups?page=${page}&limit=20`);

  return (
    <main className="shell grid">
      <Nav />
      <AdminNav />
      <div className="searchRow">
        <BackButton fallbackHref="/admin" />
      </div>
      <section className="grid">
        {writeups.items.map((writeup) => (
          <article key={writeup.id} className="card result">
            <div className="label">{writeup.event ?? "Unknown event"}</div>
            <h2>{writeup.title}</h2>
            <div className="chips">
              {writeup.challenge ? <span className="chip">{writeup.challenge}</span> : null}
              {writeup.category ? <span className="chip">{writeup.category}</span> : null}
              {writeup.team ? <span className="chip">{writeup.team}</span> : null}
            </div>
            <div className="muted">{writeup.external_id}</div>
            <div className="searchRow">
              <Link className="button" href={`/admin/writeups/${writeup.id}/edit`}>
                Edit
              </Link>
              <Link className="adminNavLink" href={`/writeups/${writeup.id}`}>
                View
              </Link>
              <DeleteWriteupButton writeupId={writeup.id} />
            </div>
          </article>
        ))}
      </section>
      <Pagination page={writeups.page} totalPages={writeups.total_pages} makeHref={(nextPage) => `/admin/writeups?page=${nextPage}`} />
    </main>
  );
}
