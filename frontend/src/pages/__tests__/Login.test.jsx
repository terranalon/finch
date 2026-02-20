import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../contexts", () => ({
  useAuth: vi.fn(),
  useTheme: vi.fn(),
}));

const mockLogin = vi.fn();
const mockNavigate = vi.fn();

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useNavigate: () => mockNavigate };
});

import { useAuth, useTheme } from "../../contexts";
import Login from "../Login";

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  );
}

describe("Login", () => {
  beforeEach(() => {
    mockLogin.mockClear();
    mockNavigate.mockClear();
    useAuth.mockReturnValue({ login: mockLogin });
    useTheme.mockReturnValue({ theme: "light", setTheme: vi.fn() });
  });

  it("renders inside AuthLayout with split-panel branding", () => {
    renderLogin();
    expect(screen.getByText("$247,832.15")).toBeInTheDocument();
  });

  it("renders the sign-in form with email and password fields", () => {
    renderLogin();
    expect(screen.getByLabelText(/email or username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("renders 'Create one' link below the submit button (not as subtitle)", () => {
    renderLogin();
    const link = screen.getByRole("link", { name: /create one/i });
    expect(link).toHaveAttribute("href", "/register");
  });

  it("renders 'Try the demo' text link", () => {
    renderLogin();
    expect(screen.getByRole("button", { name: /try the demo/i })).toBeInTheDocument();
  });

  it("does not render a ThemeToggle", () => {
    renderLogin();
    expect(screen.queryByTitle(/toggle theme/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/toggle.*theme/i)).not.toBeInTheDocument();
  });

  it("renders forgot password link", () => {
    renderLogin();
    expect(screen.getByRole("link", { name: /forgot password/i })).toHaveAttribute("href", "/forgot-password");
  });

  it("calls login and navigates on successful submit", async () => {
    mockLogin.mockResolvedValue({});
    renderLogin();

    fireEvent.change(screen.getByLabelText(/email or username/i), { target: { value: "user@test.com" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("user@test.com", "password123");
      expect(mockNavigate).toHaveBeenCalledWith("/");
    });
  });

  it("calls demo login when 'Try the demo' is clicked", async () => {
    mockLogin.mockResolvedValue({});
    renderLogin();

    fireEvent.click(screen.getByRole("button", { name: /try the demo/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("demo@finch.com", "Demo1234");
    });
  });

  it("shows error message on login failure", async () => {
    mockLogin.mockRejectedValue(new Error("Invalid credentials"));
    renderLogin();

    fireEvent.change(screen.getByLabelText(/email or username/i), { target: { value: "bad" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "bad" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
    });
  });
});
