import Link from "next/link";

export function AdminNav() {
  return (
    <div className="adminNav">
      <Link href="/admin" className="adminNavLink">
        Overview
      </Link>
      <Link href="/admin/writeups" className="adminNavLink">
        Writeups
      </Link>
      <Link href="/admin/jobs" className="adminNavLink">
        Jobs
      </Link>
      <Link href="/admin/writeups/new" className="adminNavLink">
        Add Writeup
      </Link>
    </div>
  );
}
