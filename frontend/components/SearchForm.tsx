"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export function SearchForm({ initialQuery = "" }: { initialQuery?: string }) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    router.push(`/search?q=${encodeURIComponent(query)}`);
  }

  return (
    <form className="searchRow" onSubmit={onSubmit}>
      <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder='Search offline writeups, e.g. "invalid next size (fast)"' />
      <button type="submit">Search</button>
    </form>
  );
}
