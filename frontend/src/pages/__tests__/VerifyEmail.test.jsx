import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../contexts", () => ({
  useTheme: vi.fn(),
}));

vi.mock("../../lib/api", () => ({
  verifyEmail: vi.fn(),
}));

import { useTheme } from "../../contexts";
import { verifyEmail } from "../../lib/api";
import VerifyEmail from "../VerifyEmail";

function renderPage(search = "?token=valid-token") {
  return render(
    <MemoryRouter initialEntries={[`/verify-email${search}`]}>
      <VerifyEmail />
    </MemoryRouter>
  );
}

describe("VerifyEmail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useTheme.mockReturnValue({ theme: "light", setTheme: vi.fn() });
    verifyEmail.mockReturnValue(new Promise(() => {}));
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

  it("shows verifying state initially", () => {
    renderPage();
    expect(screen.getByText(/verifying your email/i)).toBeInTheDocument();
  });

  it("shows success state after verification", async () => {
    verifyEmail.mockResolvedValue({});
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Email verified!")).toBeInTheDocument();
      expect(screen.getAllByRole("link", { name: /sign in/i }).length).toBeGreaterThan(0);
    });
  });

  it("shows error state on failure", async () => {
    verifyEmail.mockRejectedValue(new Error("Token expired"));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Verification failed")).toBeInTheDocument();
      expect(screen.getByText("Token expired")).toBeInTheDocument();
    });
  });

  it("shows error when no token provided", async () => {
    renderPage("");

    await waitFor(() => {
      expect(screen.getByText("Verification failed")).toBeInTheDocument();
      expect(screen.getByText("No verification token provided")).toBeInTheDocument();
    });
  });
});
