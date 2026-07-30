import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    useTypeScriptCli: true,
    proxyClientMaxBodySize: "1gb",
  },
  async rewrites() {
    const internalApiBase = process.env.INTERNAL_API_BASE ?? "http://backend:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${internalApiBase}/api/:path*`,
      },
      {
        source: "/docs",
        destination: `${internalApiBase}/docs`,
      },
      {
        source: "/redoc",
        destination: `${internalApiBase}/redoc`,
      },
      {
        source: "/openapi.json",
        destination: `${internalApiBase}/openapi.json`,
      },
      {
        source: "/health",
        destination: `${internalApiBase}/health`,
      },
      {
        source: "/ready",
        destination: `${internalApiBase}/ready`,
      },
    ];
  },
};

export default nextConfig;
