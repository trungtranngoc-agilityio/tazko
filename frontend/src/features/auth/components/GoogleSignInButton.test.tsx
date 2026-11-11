import { render, screen } from "@testing-library/react";
import { GoogleSignInButton } from "./GoogleSignInButton";

describe("GoogleSignInButton", () => {
  it("starts sign-in on the API host", () => {
    render(<GoogleSignInButton />);

    const link = screen.getByRole("link", { name: "Sign in with Google" });
    expect(link.getAttribute("href")).toMatch(/\/auth\/google\/start$/);
  });
});
