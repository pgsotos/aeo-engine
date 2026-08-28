import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle for a slim Docker runtime image.
  output: "standalone",
};

export default nextConfig;
