import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL?.replace(/\/$/, "");
const backendApiUrl = backendUrl ? (backendUrl.endsWith("/api") ? backendUrl : `${backendUrl}/api`) : undefined;

const nextConfig: NextConfig = {
  async rewrites() {
    if (!backendApiUrl) {
      return [];
    }

    return [
      {
        source: "/api/:path*",
        destination: `${backendApiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
