/** @type {import('next').NextConfig} */
const basePath = process.env.NEXT_BASE_PATH || "";
const nextConfig = {
  output: "export",
  trailingSlash: true,
  basePath,
  images: { unoptimized: true },
  poweredByHeader: false,
};
export default nextConfig;
