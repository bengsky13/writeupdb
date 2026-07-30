"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { MarkdownRenderer } from "./MarkdownRenderer";

type Attachment = {
  id: number;
  filename: string;
  type?: string | null;
  mime_type: string;
  size_bytes: number;
};

function inferLanguage(filename: string, mimeType: string) {
  const extension = filename.split(".").pop()?.toLowerCase();
  const byExtension: Record<string, string> = {
    py: "python",
    js: "javascript",
    ts: "typescript",
    php: "php",
    c: "c",
    cc: "cpp",
    cpp: "cpp",
    rs: "rust",
    go: "go",
    java: "java",
    kt: "kotlin",
    swift: "swift",
    sh: "bash",
    sql: "sql",
    json: "json",
    xml: "xml",
    yml: "yaml",
    yaml: "yaml",
    toml: "toml",
    ini: "ini",
    conf: "ini",
    txt: "text",
  };
  if (extension && byExtension[extension]) {
    return byExtension[extension];
  }
  if (mimeType.includes("javascript")) {
    return "javascript";
  }
  if (mimeType.includes("json")) {
    return "json";
  }
  if (mimeType.includes("xml")) {
    return "xml";
  }
  return "text";
}

export function AttachmentPreviewList({
  writeupId,
  attachments,
}: {
  writeupId: number;
  attachments: Attachment[];
}) {
  const [active, setActive] = useState<Attachment | null>(null);
  const [content, setContent] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!active) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [active]);

  async function openAttachment(attachment: Attachment) {
    setActive(attachment);
    setContent("");
    setStatus("loading");
    try {
      const response = await fetch(`/api/writeups/${writeupId}/attachments/${attachment.id}`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`request failed with ${response.status}`);
      }
      setContent(await response.text());
      setStatus("idle");
    } catch {
      setStatus("error");
    }
  }

  const language = active ? inferLanguage(active.filename, active.mime_type) : "text";

  return (
    <>
      <div className="grid">
        <span className="label">Attachments</span>
        {attachments.map((attachment) => (
          <button
            key={attachment.id}
            type="button"
            className="adminNavLink attachmentButton"
            onClick={() => openAttachment(attachment)}
          >
            {attachment.filename} ({attachment.type ?? "file"})
          </button>
        ))}
      </div>
      {mounted && active
        ? createPortal(
            <div className="modalBackdrop" onClick={() => setActive(null)}>
              <div className="modalCard" onClick={(event) => event.stopPropagation()}>
                <div className="modalHeader">
                  <div>
                    <div className="label">Attachment Preview</div>
                    <h3 className="modalTitle">{active.filename}</h3>
                  </div>
                  <button type="button" className="button modalClose" onClick={() => setActive(null)}>
                    Close
                  </button>
                </div>
                {status === "loading" ? <div className="muted">Loading attachment...</div> : null}
                {status === "error" ? <div className="muted">Failed to load attachment preview.</div> : null}
                {status === "idle" && content ? (
                  <MarkdownRenderer content={`\`\`\`${language}\n${content}\n\`\`\``} className="modalMarkdown" />
                ) : null}
              </div>
            </div>,
            document.body,
          )
        : null}
    </>
  );
}
