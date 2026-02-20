import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../contexts", () => ({
  useTheme: vi.fn(),
}));

vi.mock("../../lib/api", () => ({
  forgotPassword: vi.fn(),
}));

import { useTheme } from "../../contexts";
import { forgotPassword } from "../../lib/api";
import ForgotPassword from "../ForgotPassword";

function renderPage() {
  return render(
    <MemoryRouter>
      <ForgotPassword />
    </MemoryRouter>
  );
}

describe("ForgotPassword", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useTheme.mockReturnValue({ theme: "light", setTheme: vi.fn() });
  });

  it("renders inside AuthLayout with split-panel branding", () => {
    renderPage();
    expect(screen.getByText("$247,832.15")).toBeInTheDocument();
  });

  it("does not render a ThemeToggle", () => {
    renderPage();
    expect(screen.queryByTitle(/toggle theme/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/toggle.*theme/i)).not.toBeInTheDocument();
  });

  it("renders the form with email input", () => {
    renderPage();
    expect(screen.getByText("Reset your password")).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send reset link/i })).toBeInTheDocument();
  });

  it("renders sign-in link", () => {
    renderPage();
    const links = screen.getAllByRole("link", { name: /sign in/i });
    expect(links.length).toBeGreaterThanOrEqual(1);
  });

  it("shows submitted state after success", async () => {
    forgotPassword.mockResolvedValue({});
    renderPage();

    fireEvent.change(screen.getByLabelText(/email address/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));

    await waitFor(() => {
      expect(screen.getByText("Check your email")).toBeInTheDocument();
      expect(screen.getByText(/test@example.com/)).toBeInTheDocument();
      expect(screen.getByText(/expire in 1 hour/i)).toBeInTheDocument();
    });
  });

  it("submitted state still renders inside AuthLayout", async () => {
    forgotPassword.mockResolvedValue({});
    renderPage();

    fireEvent.change(screen.getByLabelText(/email address/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));

    await waitFor(() => {
      expect(screen.getByText("$247,832.15")).toBeInTheDocument();
    });
  });

  it("shows error on failure", async () => {
    forgotPassword.mockRejectedValue(new Error("Rate limited"));
    renderPage();

    fireEvent.change(screen.getByLabelText(/email address/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send reset link/i }));

    await waitFor(() => {
      expect(screen.getByText("Rate limited")).toBeInTheDocument();
    });
  });
});
