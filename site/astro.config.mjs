import { defineConfig } from "astro/config";

// Deployed to Cloudflare Pages at hagbert.pages.dev, served from the root, so
// base is "/". If you switch to a custom domain or GitHub Pages, change site
// and base here together with site.config.yaml -> site.url.
export default defineConfig({
  site: "https://hagbert.pages.dev",
  base: "/",
});
