import Link from "next/link";

import { AdminNav } from "../../components/AdminNav";
import { BackButton } from "../../components/BackButton";
import { Nav } from "../../components/Nav";

export default function AdminPage() {
  return (
    <main className="shell grid">
      <Nav />
      <AdminNav />
      <div className="searchRow">
        <BackButton fallbackHref="/" />
      </div>
      <section className="grid stats">
        <Link className="card" href="/admin/jobs"><div className="label">Ingestion</div><div className="value">Jobs</div></Link>
        <Link className="card" href="/admin/writeups"><div className="label">Collection</div><div className="value">Writeups</div></Link>
        <Link className="card" href="/admin/writeups/new"><div className="label">Manual Input</div><div className="value">Upload</div></Link>
      </section>
    </main>
  );
}
