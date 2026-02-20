import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../contexts", () => ({
  useTheme: vi.fn(),
}));

vi.mock("../../lib/api", () => ({
  register: vi.fn(),
}));

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useNavigate: () => mockNavigate };
});

import { useTheme } from "../../contexts";
import { register } from "../../lib/api";
import Register from "../Register";

function renderRegister() {
  return render(
    <MemoryRouter>
      <Register />
    </MemoryRouter>
  );
}

describe("Register", () => {
  beforeEach(() => {
    register.mockClear();
    mockNavigate.mockClear();
    useTheme.mockReturnValue({ theme: "light", setTheme: vi.fn() });
  });

  it("renders inside AuthLayout with split-panel branding", () => {
    renderRegister();
    expect(screen.getByText("$247,832.15")).toBeInTheDocument();
  });

  it("renders all four form fields", () => {
    renderRegister();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^username$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
  });

  it("renders 'Sign in' link below the submit button", () => {
    renderRegister();
    // AuthNavbar also has a "Sign In" link on the register page, so we use getAllByRole
    const links = screen.getAllByRole("link", { name: /sign in/i });
    expect(links.every((l) => l.getAttribute("href") === "/login")).toBe(true);
  });

  it("renders create account button", () => {
    renderRegister();
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });

  it("does not render a ThemeToggle", () => {
    renderRegister();
    expect(screen.queryByTitle(/toggle theme/i)).not.toBeInTheDocument();
  });

  it("shows error when passwords do not match", async () => {
    renderRegister();

    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText(/^username$/i), { target: { value: "user1" } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: "Password1" } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: "Different1" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
    expect(register).not.toHaveBeenCalled();
  });

  it("calls register and navigates on success", async () => {
    register.mockResolvedValue({});
    renderRegister();

    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText(/^username$/i), { target: { value: "user1" } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: "Password1" } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: "Password1" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(register).toHaveBeenCalledWith("a@b.com", "Password1", "user1");
      expect(mockNavigate).toHaveBeenCalledWith("/verification-pending", { state: { email: "a@b.com" } });
    });
  });
});
