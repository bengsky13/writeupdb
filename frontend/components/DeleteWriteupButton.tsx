"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function DeleteWriteupButton({
  writeupId,
  label = "Delete",
  className = "button dangerButton",
}: {
  writeupId: number;
  label?: string;
  className?: string;
}) {
  const router = useRouter();
  const [isDeleting, setIsDeleting] = useState(false);

  async function onDelete() {
    if (!window.confirm("Delete this writeup? This cannot be undone.")) {
      return;
    }

    setIsDeleting(true);
    try {
      const response = await fetch(`/api/admin/writeups/${writeupId}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const body = await response.text();
        throw new Error(body || `Request failed with ${response.status}`);
      }
      router.refresh();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "Delete failed.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <button
      type="button"
      className={className}
      disabled={isDeleting}
      onClick={() => {
        void onDelete();
      }}
    >
      {isDeleting ? "Deleting..." : label}
    </button>
  );
}
