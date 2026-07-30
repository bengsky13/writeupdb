import { AttachmentPreviewList } from "../../../components/AttachmentPreviewList";
import { BackButton } from "../../../components/BackButton";
import { EventLink } from "../../../components/EventLink";
import { MarkdownRenderer } from "../../../components/MarkdownRenderer";
import { Nav } from "../../../components/Nav";
import { fetchJson } from "../../../lib/api";

type WriteupResponse = {
  id: number;
  title: string;
  event?: string | null;
  event_year?: number | null;
  challenge?: string | null;
  category?: string | null;
  team?: string | null;
  content: string;
  metadata: Record<string, unknown>;
  attachments: Array<{
    id: number;
    attachment_id: string;
    filename: string;
    type?: string | null;
    mime_type: string;
    size_bytes: number;
  }>;
};

export default async function WriteupDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const writeup = await fetchJson<WriteupResponse>(`/api/writeups/${id}`);
  const customTags = Array.isArray(writeup.metadata.custom_tags)
    ? (writeup.metadata.custom_tags as string[])
    : [];
  return (
    <main className="shell grid">
      <Nav />
      <div className="searchRow">
        <BackButton fallbackHref="/" />
      </div>
      <section className="twoCol">
        <article className="card grid contentCard">
          <EventLink event={writeup.event} eventYear={writeup.event_year} />
          <h1>{writeup.title}</h1>
          <div className="chips">
            {writeup.challenge ? <span className="chip">{writeup.challenge}</span> : null}
            {writeup.category ? <span className="chip">{writeup.category}</span> : null}
            {writeup.team ? <span className="chip">{writeup.team}</span> : null}
            {customTags.map((tag) => <span key={tag} className="chip">{tag}</span>)}
          </div>
          <MarkdownRenderer content={writeup.content} />
        </article>
        <aside className="card grid metadataCard">
          <span className="label">Metadata</span>
          {writeup.attachments.length ? (
            <AttachmentPreviewList writeupId={writeup.id} attachments={writeup.attachments} />
          ) : null}
          <div className="code metadataCode">{JSON.stringify(writeup.metadata, null, 2)}</div>
        </aside>
      </section>
    </main>
  );
}
