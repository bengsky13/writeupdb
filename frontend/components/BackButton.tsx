"use client";

import { useRouter } from "next/navigation";

type BackButtonProps = {
  fallbackHref: string;
  label?: string;
};

export function BackButton({ fallbackHref, label = "Back" }: BackButtonProps) {
  const router = useRouter();

  return (
    <button
      type="button"
      className="adminNavLink backButton"
      onClick={() => {
        if (window.history.length > 1) {
          router.back();
          return;
        }
        router.push(fallbackHref);
      }}
    >
      {label}
    </button>
  );
}
