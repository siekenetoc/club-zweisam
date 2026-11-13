import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import { viteStaticCopy } from "vite-plugin-static-copy";

const projectRoot = fileURLToPath(new URL(".", import.meta.url));
const outDir = process.env.VITE_OUT_DIR || fileURLToPath(new URL("./dist", import.meta.url));

export default defineConfig({
  root: projectRoot,
  build: {
    outDir,
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL("./src/main.js", import.meta.url)),
      },
      output: {
        entryFileNames: "js/[name].js",
        chunkFileNames: "js/[name].js",
        assetFileNames: (assetInfo) => {
          const name = assetInfo.name || "";
          if (name.endsWith(".css")) {
            return "css/[name][extname]";
          }
          return "assets/[name][extname]";
        },
      },
    },
  },
  plugins: [
    viteStaticCopy({
      targets: [
        {
          src: "node_modules/tinymce/**/*",
          dest: "tinymce",
          structured: true,
        },
      ],
    }),
  ],
});
