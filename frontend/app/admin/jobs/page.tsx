import { BackButton } from "../../../components/BackButton";
import { AdminNav } from "../../../components/AdminNav";
import { ClearAllJobsButton } from "../../../components/ClearAllJobsButton";
import { Nav } from "../../../components/Nav";
import { Pagination } from "../../../components/Pagination";
import { fetchJson } from "../../../lib/api";

type Job = { id: string; status: string; external_id?: string | null };
type PaginatedResponse<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export default async function AdminJobsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const params = await searchParams;
  const page = Math.max(Number(params.page ?? "1") || 1, 1);
  const jobs = await fetchJson<PaginatedResponse<Job>>(`/api/admin/jobs?page=${page}&limit=20`);

  return (
    <main className="shell grid">
      <Nav />
      <AdminNav />
      <div className="searchRow">
        <BackButton fallbackHref="/admin" />
        <ClearAllJobsButton />
      </div>
      <div className="grid">
        {jobs.items.map((job) => (
          <div key={job.id} className="card">
            <div className="label">{job.status}</div>
            <div>{job.external_id}</div>
            <div className="muted">{job.id}</div>
          </div>
        ))}
      </div>
      <Pagination page={jobs.page} totalPages={jobs.total_pages} makeHref={(nextPage) => `/admin/jobs?page=${nextPage}`} />
    </main>
  );
}
