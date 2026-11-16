import { errorText, t } from ".";

describe("t", () => {
  it("returns the English string", () => {
    expect(t("app.name")).toBe("Tazko");
  });
});

describe("errorText", () => {
  it("translates a known error code", () => {
    expect(errorText("SLUG_TAKEN")).toBe(t("error.SLUG_TAKEN"));
  });

  it("falls back to a generic message for an unknown code", () => {
    expect(errorText("SOMETHING_NEW")).toBe(t("error.UNKNOWN"));
  });

  it("never looks up keys outside the error group", () => {
    expect(errorText("app.name")).toBe(t("error.UNKNOWN"));
  });
});
