import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produces a minimal, self-contained server bundle (.next/standalone)
  // for the production Docker image — see frontend/Dockerfile.
  output: "standalone",
};

export default nextConfig;
