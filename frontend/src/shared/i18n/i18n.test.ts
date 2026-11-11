import { t } from ".";

describe("t", () => {
  it("returns the English string", () => {
    expect(t("app.name")).toBe("Tazko");
  });
});
