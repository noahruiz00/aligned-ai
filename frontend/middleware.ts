import { NextResponse, type NextRequest } from "next/server";

/**
 * UX gate only: sends people without the right cookie to the right place before a page renders.
 * The backend validates every cookie on every request; this never grants access by itself.
 */
export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const staff = req.cookies.get("aligned_staff");
  const client = req.cookies.get("aligned_client");

  if ((pathname.startsWith("/advisor") || pathname.startsWith("/admin")) && !staff) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(pathname)}`;
    return NextResponse.redirect(url);
  }
  if (pathname.startsWith("/client/") && !staff && !client) {
    const url = req.nextUrl.clone();
    url.pathname = "/discover";
    url.search = "";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/advisor/:path*", "/admin/:path*", "/client/:path*"] };
