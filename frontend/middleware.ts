import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const SESSION_COOKIE = "ctf_search_session";

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (pathname.startsWith("/api/")) {
    return NextResponse.next();
  }
  const isPublicPath =
    pathname === "/login" ||
    pathname.startsWith("/_next/") ||
    pathname === "/favicon.ico";

  const hasSession = Boolean(request.cookies.get(SESSION_COOKIE)?.value);

  if (!isPublicPath && !hasSession) {
    const target = new URL("/login", request.url);
    if (pathname !== "/") {
      target.searchParams.set("next", `${pathname}${search}`);
    }
    return NextResponse.redirect(target);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
