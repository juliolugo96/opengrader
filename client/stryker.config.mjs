/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
const config = {
  mutate: [
    "src/lib/api-client.ts:33-55",
    "src/lib/api-client.ts:70-99",
    "src/lib/api-client.ts:101-150",
    "src/lib/api-client.ts:152-210",
    "src/lib/api-client.ts:267-283",
    "src/lib/i18n.tsx:276-282",
    "src/components/billing/BillingPanel.tsx:50-59",
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
