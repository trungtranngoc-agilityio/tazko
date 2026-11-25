import js from "@eslint/js";
import { defineConfig } from "eslint/config";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

export default defineConfig(
  { ignores: ["dist", "coverage"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
      // Type information, so a deprecated API is caught before it is removed.
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    plugins: { "react-hooks": reactHooks, "react-refresh": reactRefresh },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/no-deprecated": "error",
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    },
  },
  // Layers (src/shared/README.md): app -> pages -> features -> shared.
  layer("src/pages/**", ["@/app/*"], "Pages compose features; they never import the app shell."),
  layer(
    "src/features/**",
    ["@/app/*", "@/pages/*"],
    "Features never import pages or the app shell.",
  ),
  layer(
    "src/shared/**",
    ["@/app/*", "@/pages/*", "@/features/*"],
    "shared/ is the bottom layer; it imports nothing above it.",
  ),
);

/** Forbid imports from higher layers, and deep imports into a feature (use its index.ts). */
function layer(files, forbidden, message) {
  return {
    files: [files],
    ignores: ["**/*.test.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            { group: forbidden, message },
            { group: ["@/features/*/*"], message: "Import a feature from its index.ts only." },
          ],
        },
      ],
    },
  };
}
