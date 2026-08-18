/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
const config = {
  mutate: [
    "src/lib/api-client.ts:37-53",
    "src/lib/api-client.ts:68-80",
    "src/lib/api-client.ts:83-131",
    "src/lib/api-client.ts:134-181",
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
