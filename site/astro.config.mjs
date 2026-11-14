import { defineConfig } from "astro/config";

// Project Pages URL is gunnaroi.github.io/hagbert, so base is the repo name.
// Change site/base together if a custom domain is connected (see site.config.yaml).
export default defineConfig({
  site: "https://gunnaroi.github.io/hagbert",
  base: "/hagbert",
});
