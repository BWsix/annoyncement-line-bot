/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  async redirects() {
    return [
      {
        source: "/",
        destination: "https://github.com/BWsix/annoyncement-line-bot",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
