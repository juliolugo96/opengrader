import { describe, expect, it } from "vitest";

import { translate } from "@/lib/i18n";

describe("translate", () => {
  it("translates the professor workspace in every supported language", () => {
    expect(translate("en", "nav.assignments")).toBe("Assignments");
    expect(translate("es", "nav.assignments")).toBe("Asignaciones");
    expect(translate("zh-CN", "nav.assignments")).toBe("作业");
  });

  it("interpolates values and falls back to English", () => {
    expect(translate("es", "assignments.checkCount", { count: 3 })).toBe("3 evaluaciones");
    expect(translate("zh-CN", "assignments.points", { count: 20 })).toBe("20 分");
  });
});
