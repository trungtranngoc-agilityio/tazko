import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Initials } from "./Initials";

// The prototype colours each avatar with one of five tones picked from the
// name (tone() in design/tazko-prototype.html); expected values come from it.
describe("Initials", () => {
  it.each([
    ["Harbor Studio", "c2"],
    ["Larkspur Co", "c4"],
    ["Mai Tran", "c3"],
    ["Mai Thi Tran", "c1"],
  ])("gives %s the prototype's tone %s", (name, tone) => {
    const { container } = render(<Initials name={name} />);

    expect(container.firstElementChild).toHaveAttribute("data-tone", tone);
  });

  it("uses the first letters of the first and last words, as the prototype", () => {
    const { container } = render(<Initials name="Anna Maria Tran" />);

    expect(container).toHaveTextContent("AT");
  });

  it("is 44 px at the extra-large size, for page headers", () => {
    const { container } = render(<Initials name="Harbor Studio" size="xl" />);

    expect(container.firstElementChild).toHaveClass("size-11");
  });
});
