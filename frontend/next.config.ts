import type { NextConfig } from "next";

// const nextConfig: NextConfig = {
//   /* config options here */
// };
// export default nextConfig;

/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ["via.placeholder.com"], // ✅ Allow external images
  },
};

module.exports = nextConfig;


