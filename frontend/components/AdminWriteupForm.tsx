"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

type SubmissionState =
  | { type: "idle" }
  | { type: "submitting" }
  | { type: "deleting" }
  | { type: "success"; jobId: string; message: string }
  | { type: "error"; message: string };

export type AdminWriteupFormData = {
  id?: number;
  external_id?: string;
  title?: string;
  event?: string | null;
  event_year?: number | null;
  challenge?: string | null;
  category?: string | null;
  difficulty?: string | null;
  authors?: string[];
  team?: string | null;
  language?: string | null;
  published_at?: string | null;
  content_format?: string;
  content?: string;
  metadata?: Record<string, unknown>;
};

type JobStatusResponse = {
  id: string;
  status: string;
  external_id?: string | null;
  writeup_id?: number | null;
  error?: string | null;
};

function slugify(value: string) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function AdminWriteupForm({
  initialData,
  mode = "create",
}: {
  initialData?: AdminWriteupFormData;
  mode?: "create" | "edit";
}) {
  const router = useRouter();
  const [title, setTitle] = useState(initialData?.title ?? "");
  const [externalId, setExternalId] = useState(initialData?.external_id ?? "");
  const [event, setEvent] = useState(initialData?.event ?? "");
  const [eventYear, setEventYear] = useState(initialData?.event_year?.toString() ?? "");
  const [challenge, setChallenge] = useState(initialData?.challenge ?? "");
  const [category, setCategory] = useState(initialData?.category ?? "web");
  const [difficulty, setDifficulty] = useState(initialData?.difficulty ?? "medium");
  const [authors, setAuthors] = useState(initialData?.authors?.join(", ") ?? "");
  const [team, setTeam] = useState(initialData?.team ?? "");
  const [language, setLanguage] = useState(initialData?.language ?? "en");
  const [publishedAt, setPublishedAt] = useState(initialData?.published_at ?? "");
  const [contentFormat, setContentFormat] = useState(initialData?.content_format ?? "markdown");
  const [content, setContent] = useState(initialData?.content ?? "# Title\n\n## Analysis\n\n## Exploitation\n");
  const [metadataJson, setMetadataJson] = useState(JSON.stringify(initialData?.metadata ?? {}, null, 2));
  const [customTags, setCustomTags] = useState(
    Array.isArray(initialData?.metadata?.custom_tags)
      ? (initialData?.metadata?.custom_tags as string[]).join(", ")
      : "",
  );
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [sourceFiles, setSourceFiles] = useState<File[]>([]);
  const [state, setState] = useState<SubmissionState>({ type: "idle" });

  const suggestedExternalId = useMemo(() => {
    const pieces = [event, eventYear, challenge || title].filter(Boolean).map(slugify).filter(Boolean);
    return pieces.join("-");
  }, [challenge, event, eventYear, title]);

  useEffect(() => {
    if (state.type !== "success") {
      return;
    }

    const interval = window.setInterval(async () => {
      try {
        const response = await fetch(`/api/admin/jobs/${state.jobId}`, {
          cache: "no-store",
        });
        if (!response.ok) {
          return;
        }
        const job = (await response.json()) as JobStatusResponse;
        if (job.status === "completed" && job.writeup_id) {
          window.clearInterval(interval);
          router.push(`/writeups/${job.writeup_id}`);
          return;
        }
        if (job.status === "failed") {
          window.clearInterval(interval);
          setState({
            type: "error",
            message: job.error || "The ingestion job failed.",
          });
        }
      } catch {
        return;
      }
    }, 1500);

    return () => window.clearInterval(interval);
  }, [router, state]);

  async function onFileChange(file: File | null) {
    setUploadedFile(file);
    if (!file) {
      return;
    }
    const extension = file.name.split(".").pop()?.toLowerCase();
    if (extension === "html") {
      setContentFormat("html");
    } else if (extension === "txt") {
      setContentFormat("text");
    } else {
      setContentFormat("markdown");
    }
    const text = await file.text();
    setContent(text);
    if (!title) {
      setTitle(file.name.replace(/\.[^.]+$/, ""));
    }
  }

  async function onSubmit(eventObject: FormEvent<HTMLFormElement>) {
    eventObject.preventDefault();
    setState({ type: "submitting" });

    let metadata: Record<string, unknown>;
    try {
      metadata = metadataJson.trim() ? JSON.parse(metadataJson) : {};
    } catch {
      setState({ type: "error", message: "Metadata JSON is invalid." });
      return;
    }
    metadata.custom_tags = customTags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);

    const payload = {
      external_id: externalId || suggestedExternalId,
      title,
      event: event || null,
      event_year: eventYear ? Number(eventYear) : null,
      challenge: challenge || null,
      category: category || null,
      difficulty: difficulty || null,
      authors: authors
        .split(",")
        .map((author) => author.trim())
        .filter(Boolean),
      team: team || null,
      language: language || null,
      published_at: publishedAt || null,
      source_reference: "web-admin",
      original_source_url: null,
      content_format: contentFormat,
      content,
      metadata,
      attachments: [],
    };

    if (!payload.external_id) {
      setState({ type: "error", message: "External ID is required." });
      return;
    }

    try {
      const useMultipart = Boolean(uploadedFile) || sourceFiles.length > 0;
      let response: Response;
      if (useMultipart) {
        const formData = new FormData();
        formData.append("metadata_json", JSON.stringify(payload));
        if (uploadedFile) {
          formData.append("content_file", uploadedFile);
        }
        for (const file of sourceFiles) {
          formData.append("source_files", file);
        }
        response = await fetch(
          mode === "edit" && initialData?.id
            ? `/api/admin/writeups/${initialData.id}/upload`
            : "/api/admin/ingest/upload",
          {
            method: mode === "edit" ? "PATCH" : "POST",
            body: formData,
          },
        );
      } else {
        response = await fetch(
          mode === "edit" && initialData?.id
            ? `/api/admin/writeups/${initialData.id}`
            : "/api/admin/ingest/raw",
          {
            method: mode === "edit" ? "PATCH" : "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
          },
        );
      }

      if (!response.ok) {
        const body = await response.text();
        throw new Error(body || `Request failed with ${response.status}`);
      }

      const result = (await response.json()) as { job_id: string };
      setState({
        type: "success",
        jobId: result.job_id,
        message:
          mode === "edit"
            ? "Revision queued. Waiting for reindexing to finish..."
            : "Writeup queued. Waiting for indexing to finish...",
      });
    } catch (error) {
      setState({
        type: "error",
        message: error instanceof Error ? error.message : "Submission failed.",
      });
    }
  }

  async function onDelete() {
    if (mode !== "edit" || !initialData?.id) {
      return;
    }
    if (!window.confirm(`Delete writeup "${title || initialData.external_id}"? This cannot be undone.`)) {
      return;
    }

    setState({ type: "deleting" });
    try {
      const response = await fetch(`/api/admin/writeups/${initialData.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const body = await response.text();
        throw new Error(body || `Request failed with ${response.status}`);
      }
      router.push("/admin/writeups");
      router.refresh();
    } catch (error) {
      setState({
        type: "error",
        message: error instanceof Error ? error.message : "Delete failed.",
      });
    }
  }

  return (
    <form className="grid" onSubmit={onSubmit}>
      <div className="grid formTwoCol">
        <div className="card grid">
          <div className="label">Writeup Metadata</div>
          <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Title" required />
        <input
          value={externalId}
          onChange={(event) => setExternalId(event.target.value)}
          placeholder={`External ID (default: ${suggestedExternalId || "auto-from-title"})`}
          readOnly={mode === "edit"}
        />
          <input value={event} onChange={(event) => setEvent(event.target.value)} placeholder="CTF event" />
          <input value={eventYear} onChange={(event) => setEventYear(event.target.value)} placeholder="Event year" />
          <input value={challenge} onChange={(event) => setChallenge(event.target.value)} placeholder="Challenge name" />
          <input value={authors} onChange={(event) => setAuthors(event.target.value)} placeholder="Authors, comma separated" />
          <input value={team} onChange={(event) => setTeam(event.target.value)} placeholder="Team" />
          <input value={publishedAt} onChange={(event) => setPublishedAt(event.target.value)} placeholder="Published at ISO8601" />
          <input
            value={customTags}
            onChange={(event) => setCustomTags(event.target.value)}
            placeholder="Custom tags, comma separated"
          />
          <div className="searchRow">
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              <option value="web">web</option>
              <option value="pwn">pwn</option>
              <option value="crypto">crypto</option>
              <option value="forensics">forensics</option>
              <option value="mobile">mobile</option>
              <option value="misc">misc</option>
            </select>
            <select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>
              <option value="easy">easy</option>
              <option value="medium">medium</option>
              <option value="hard">hard</option>
            </select>
            <select value={language} onChange={(event) => setLanguage(event.target.value)}>
              <option value="en">en</option>
              <option value="id">id</option>
              <option value="ja">ja</option>
            </select>
            <select value={contentFormat} onChange={(event) => setContentFormat(event.target.value)}>
              <option value="markdown">markdown</option>
              <option value="html">html</option>
              <option value="text">text</option>
            </select>
          </div>
        </div>

        <div className="card grid">
          <div className="label">Extra Metadata JSON</div>
          <textarea
            value={metadataJson}
            onChange={(event) => setMetadataJson(event.target.value)}
            placeholder='{"technologies":["Flask"],"tools":["flask-unsign"]}'
            rows={12}
          />
        </div>
      </div>

      <div className="card grid">
        <div className="label">Writeup Content</div>
        <input
          type="file"
          accept=".md,.markdown,.txt,.html,.htm"
          onChange={(event) => {
            void onFileChange(event.target.files?.[0] ?? null);
          }}
        />
        <input
          type="file"
          accept=".py,.js,.ts,.php,.c,.cc,.cpp,.rs,.go,.java,.kt,.swift,.sh,.sql,.txt"
          multiple
          onChange={(event) => {
            setSourceFiles(Array.from(event.target.files ?? []));
          }}
        />
        {sourceFiles.length > 0 ? (
          <div className="muted">{sourceFiles.length} source file(s) selected.</div>
        ) : null}
        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder="Markdown, HTML, or plain text. You can also upload a file above."
          rows={20}
          required
        />
      </div>

      <div className="searchRow">
        <button className="button" type="submit" disabled={state.type === "submitting" || state.type === "deleting"}>
          {state.type === "submitting" ? "Submitting..." : mode === "edit" ? "Save Changes" : "Submit Writeup"}
        </button>
        {mode === "edit" ? (
          <button
            className="button dangerButton"
            type="button"
            disabled={state.type === "submitting" || state.type === "deleting"}
            onClick={() => {
              void onDelete();
            }}
          >
            {state.type === "deleting" ? "Deleting..." : "Delete Writeup"}
          </button>
        ) : null}
        {state.type === "success" ? <div className="card">{state.message} Job: {state.jobId}</div> : null}
        {state.type === "error" ? <div className="card">Error: {state.message}</div> : null}
      </div>
    </form>
  );
}
