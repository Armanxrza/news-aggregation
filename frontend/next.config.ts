import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  ...(process.env.NEXT_PUBLIC_BASE_PATH ? { basePath: process.env.NEXT_PUBLIC_BASE_PATH } : {}),
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "https://api.sajhanews.yagyatech.com.np/api/:path*",
      },
    ];
  },
};

export default nextConfig;
