import { describe, expect, it } from "vitest";
import { size } from "./size";

describe("size", () => {
  it.each([
    [0, "0 B"],
    [512 * 1024 * 1024, "512 MB"],
    [2.5 * 1024 ** 3, "2.5 GB"],
    [1024 * 1024 - 1, "1 MB"],
  ])("writes %d bytes as %s", (bytes, text) => {
    expect(size(bytes)).toBe(text);
  });
});
