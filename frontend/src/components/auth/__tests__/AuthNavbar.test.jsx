import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import AuthNavbar from "../AuthNavbar";

function renderNavbar(page) {
  return render(
    <MemoryRouter>
      <AuthNavbar page={page} />
    </MemoryRouter>
  );
}

describe("AuthNavbar", () => {
  it("renders the Finch logo linking to home", () => {
    renderNavbar("login");
    const logoLink = screen.getByRole("link", { name: /finch/i });
    expect(logoLink).toHaveAttribute("href", "/");
  });

  it("renders a Home back link", () => {
    renderNavbar("login");
    const backLink = screen.getByRole("link", { name: /home/i });
    expect(backLink).toHaveAttribute("href", "/");
  });

  it("shows Get Started link on the login page", () => {
    renderNavbar("login");
    expect(screen.getByRole("link", { name: /get started/i })).toHaveAttribute("href", "/register");
  });

  it("shows Sign In link on the register page", () => {
    renderNavbar("register");
    expect(screen.getByRole("link", { name: /sign in/i })).toHaveAttribute("href", "/login");
  });

  it("does not show Sign In on the login page", () => {
    renderNavbar("login");
    expect(screen.queryByRole("link", { name: /^sign in$/i })).not.toBeInTheDocument();
  });
});
