import { AdminWriteupForm } from "../../../../components/AdminWriteupForm";
import { AdminNav } from "../../../../components/AdminNav";
import { BackButton } from "../../../../components/BackButton";
import { Nav } from "../../../../components/Nav";

export default function AdminWriteupNewPage() {
  return (
    <main className="shell grid">
      <Nav />
      <AdminNav />
      <div className="searchRow">
        <BackButton fallbackHref="/admin/writeups" />
      </div>
      <section className="card grid">
        <h1>Manual Writeup Submission</h1>
        <p className="muted">
          Submit a writeup directly from the browser. This uses the admin ingestion API and queues the document for parsing, chunking, embedding, and indexing.
        </p>
        <AdminWriteupForm />
      </section>
    </main>
  );
}
