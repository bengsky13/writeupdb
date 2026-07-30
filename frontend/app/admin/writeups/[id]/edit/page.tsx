import { AdminWriteupForm, type AdminWriteupFormData } from "../../../../../components/AdminWriteupForm";
import { AdminNav } from "../../../../../components/AdminNav";
import { BackButton } from "../../../../../components/BackButton";
import { Nav } from "../../../../../components/Nav";
import { fetchJson } from "../../../../../lib/api";

export default async function AdminWriteupEditPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const writeup = await fetchJson<AdminWriteupFormData>(`/api/admin/writeups/${id}`);

  return (
    <main className="shell grid">
      <Nav />
      <AdminNav />
      <div className="searchRow">
        <BackButton fallbackHref="/admin/writeups" />
      </div>
      <section className="card grid">
        <h1>Edit Writeup</h1>
        <p className="muted">
          Saving changes creates a new revision and reindexes the updated content.
        </p>
        <AdminWriteupForm initialData={{ ...writeup, id: Number(id) }} mode="edit" />
      </section>
    </main>
  );
}
