import { cpSync, existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";

const projectRoot = process.cwd();
const standaloneRoot = join(projectRoot, ".next", "standalone");
const standaloneNext = join(standaloneRoot, ".next");

mkdirSync(standaloneNext, { recursive: true });
cpSync(join(projectRoot, ".next", "static"), join(standaloneNext, "static"), {
  recursive: true
});

const publicDirectory = join(projectRoot, "public");
if (existsSync(publicDirectory)) {
  cpSync(publicDirectory, join(standaloneRoot, "public"), { recursive: true });
}
