"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function ClearAllJobsButton({
  label = "Clear All Jobs",
  className = "button dangerButton",
}: {
  label?: string;
  className?: string;
}) {
  const router = useRouter();
  const [isClearing, setIsClearing] = useState(false);

  async function onClear() {
    if (!window.confirm("Clear all job entries? This only removes job records.")) {
      return;
    }

    setIsClearing(true);
    try {
      const response = await fetch("/api/admin/jobs", {
        method: "DELETE",
      });
      if (!response.ok) {
        const body = await response.text();
        throw new Error(body || `Request failed with ${response.status}`);
      }
      router.refresh();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "Clear failed.");
    } finally {
      setIsClearing(false);
    }
  }

  return (
    <button
      type="button"
      className={className}
      disabled={isClearing}
      onClick={() => {
        void onClear();
      }}
    >
      {isClearing ? "Clearing..." : label}
    </button>
  );
}
