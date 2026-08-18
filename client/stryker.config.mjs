/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
const config = {
  mutate: [
    "src/lib/api-client.ts:33-49",
    "src/lib/api-client.ts:64-77",
    "src/lib/utils.ts:30-38",
    "src/lib/utils.ts:48-68",
    "src/lib/utils.ts:78-92"
  ],
  testRunner: "vitest",
  vitest: {
    configFile: "vitest.config.ts",
    related: true
  },
  reporters: ["clear-text", "progress", "html"],
  htmlReporter: { fileName: "reports/mutation/index.html" },
  thresholds: { high: 90, low: 80, break: 75 },
  concurrency: 2,
  timeoutMS: 10_000
};

export default config;
