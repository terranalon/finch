import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../contexts", () => ({
  useTheme: vi.fn(),
}));

vi.mock("../../lib/api", () => ({
  resetPassword: vi.fn(),
}));

import { useTheme } from "../../contexts";
import { resetPassword } from "../../lib/api";
import ResetPassword from "../ResetPassword";

function renderPage(search = "?token=valid-token") {
  return render(
    <MemoryRouter initialEntries={[`/reset-password${search}`]}>
      <ResetPassword />
    </MemoryRouter>
  );
}

describe("ResetPassword", () => {
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

  it("renders password form when token is present", () => {
    renderPage();
    expect(screen.getByText("Set new password")).toBeInTheDocument();
    expect(screen.getByLabelText("New password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm new password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reset password/i })).toBeInTheDocument();
  });

  it("renders error state when no token", () => {
    renderPage("");
    expect(screen.getByText("Invalid reset link")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /request a new link/i })).toBeInTheDocument();
  });

  it("no-token error state still renders inside AuthLayout", () => {
    renderPage("");
    expect(screen.getByText("$247,832.15")).toBeInTheDocument();
  });

  it("shows success state after password reset", async () => {
    resetPassword.mockResolvedValue({});
    renderPage();

    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "NewPass123" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "NewPass123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /reset password/i }));

    await waitFor(() => {
      expect(screen.getByText(/password reset successful/i)).toBeInTheDocument();
      const links = screen.getAllByRole("link", { name: /sign in/i });
      expect(links.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("success state still renders inside AuthLayout", async () => {
    resetPassword.mockResolvedValue({});
    renderPage();

    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "NewPass123" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "NewPass123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /reset password/i }));

    await waitFor(() => {
      expect(screen.getByText("$247,832.15")).toBeInTheDocument();
    });
  });

  it("shows error for mismatched passwords", async () => {
    renderPage();

    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "NewPass123" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "Different123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /reset password/i }));

    await waitFor(() => {
      expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
    });
  });
});
