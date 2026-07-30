"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function LogoutButton() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function onLogout() {
    setIsSubmitting(true);
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
      });
    } finally {
      router.push("/login");
      router.refresh();
      setIsSubmitting(false);
    }
  }

  return (
    <button type="button" className="adminNavLink navButton" onClick={() => void onLogout()} disabled={isSubmitting}>
      {isSubmitting ? "Signing out..." : "Logout"}
    </button>
  );
}
