import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../../contexts", () => ({
  useTheme: vi.fn(),
}));

import { useTheme } from "../../../contexts";
import AuthLayout from "../AuthLayout";

const mockSetTheme = vi.fn();

function renderLayout(page = "login", children = <div>Form content</div>) {
  return render(
    <MemoryRouter>
      <AuthLayout page={page}>{children}</AuthLayout>
    </MemoryRouter>
  );
}

describe("AuthLayout", () => {
  beforeEach(() => {
    mockSetTheme.mockClear();
    useTheme.mockReturnValue({
      theme: "light",
      setTheme: mockSetTheme,
    });
  });

  it("renders children in the form panel", () => {
    renderLayout("login", <div>My login form</div>);
    expect(screen.getByText("My login form")).toBeInTheDocument();
  });

  it("renders the AuthNavbar", () => {
    renderLayout("login");
    expect(screen.getByRole("link", { name: /finch/i })).toBeInTheDocument();
  });

  it("renders the branding headline", () => {
    renderLayout("login");
    expect(screen.getByText(/know your/i)).toBeInTheDocument();
    expect(screen.getByText(/real/i)).toBeInTheDocument();
    expect(screen.getByText(/performance/i)).toBeInTheDocument();
  });

  it("renders value propositions", () => {
    renderLayout("login");
    expect(screen.getByText(/automatic daily transaction sync/i)).toBeInTheDocument();
  });

  it("renders the mini dashboard mockup", () => {
    renderLayout("login");
    expect(screen.getByText("$247,832.15")).toBeInTheDocument();
  });

  it("forces light mode when theme is dark", () => {
    useTheme.mockReturnValue({
      theme: "dark",
      setTheme: mockSetTheme,
    });
    renderLayout("login");
    expect(mockSetTheme).toHaveBeenCalledWith("light");
  });

  it("does not call setTheme when already light", () => {
    renderLayout("login");
    expect(mockSetTheme).not.toHaveBeenCalled();
  });

  it("passes page prop to AuthNavbar", () => {
    renderLayout("register");
    // Register page shows "Sign In" link in navbar
    expect(screen.getByRole("link", { name: /sign in/i })).toBeInTheDocument();
  });
});
