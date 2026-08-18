process.env.HOSTNAME ??= "127.0.0.1";
process.env.PORT ??= "3100";

await import("../.next/standalone/server.js");
