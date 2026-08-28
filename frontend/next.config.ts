import type { NextConfig } from "next";

// The Docker build sets BUILD_STANDALONE=1 to emit a self-contained server
// bundle. Vercel does its own output tracing and fails on `output: standalone`,
// so it must stay off there.
const nextConfig: NextConfig = {
  ...(process.env.BUILD_STANDALONE === "1"
    ? { output: "standalone" as const }
    : {}),
};

export default nextConfig;
