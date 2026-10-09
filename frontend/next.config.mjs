/** @type {import('next').NextConfig} */
// The browser only ever talks to this origin; /api/* is proxied to the FastAPI backend so the
// HttpOnly session cookies are first-party in every deployment (set API_URL on the host).
const API_URL = process.env.API_URL || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/:path*` }];
  },
  reactStrictMode: true,
};

export default nextConfig;
