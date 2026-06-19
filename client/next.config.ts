import type { NextConfig } from "next";

const backendUrl = process.env.API_BACKEND_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },

  reactCompiler: true,
  turbopack: {
    root: process.cwd(),
  },

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/auth/:path*",
        destination: `${backendUrl}/auth/:path*`,
      },
    ];
  },
};

export default nextConfig;
