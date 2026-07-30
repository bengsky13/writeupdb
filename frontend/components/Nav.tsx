import Link from "next/link";

import { LogoutButton } from "./LogoutButton";

export function Nav() {
  return (
    <div className="nav">
      <Link href="/"><strong>CTF Search</strong></Link>
      <div className="navLinks">
        <Link href="/search?q=ret2libc">Search</Link>
        <Link href="/events">Events</Link>
        <Link href="/admin">Admin</Link>
        <LogoutButton />
      </div>
    </div>
  );
}
