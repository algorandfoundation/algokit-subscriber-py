// @ts-check
import starlight from "@astrojs/starlight";
import { defineConfig } from "astro/config";
import remarkGithubAlerts from "remark-github-alerts";

export default defineConfig({
  site: "https://algorandfoundation.github.io",
  base: "/algokit-subscriber-py/",
  trailingSlash: "always",
  markdown: {
    remarkPlugins: [remarkGithubAlerts],
  },
  integrations: [
    starlight({
      title: "AlgoKit Subscriber Python",
      tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 4 },
      customCss: [
        "./src/styles/api-reference.css",
        "remark-github-alerts/styles/github-colors-light.css",
        "remark-github-alerts/styles/github-colors-dark-media.css",
        "remark-github-alerts/styles/github-base.css",
      ],
      social: [
        {
          icon: "github",
          label: "GitHub",
          href: "https://github.com/algorandfoundation/algokit-subscriber-py",
        },
        {
          icon: "discord",
          label: "Discord",
          href: "https://discord.gg/algorand",
        },
      ],
      sidebar: [
        { label: "Home", link: "/" },
        {
          label: "Getting Started",
          items: [{ slug: "tutorials/quick-start" }],
        },
        {
          label: "Guides",
          items: [
            { slug: "guide/subscriber" },
            { slug: "guide/subscriptions" },
          ],
        },
        {
          label: "Concepts",
          items: [
            { slug: "concepts/sync-behaviour" },
            { slug: "concepts/low-latency" },
            { slug: "concepts/watermarking" },
            { slug: "concepts/filtering" },
            { slug: "concepts/arc28-events" },
            { slug: "concepts/emit-arc28-events" },
            { slug: "concepts/inner-transactions" },
            { slug: "concepts/state-proofs" },
            { slug: "concepts/fast-catchup" },
          ],
        },
        {
          label: "API Reference",
          collapsed: true,
          items: [
            {
              slug: "api/algokit_subscriber",
              label: "algokit_subscriber Index",
            },
            {
              label: "types",
              collapsed: true,
              autogenerate: { directory: "api/algokit_subscriber/types" },
            },
          ],
        },
      ],
    }),
  ],
});