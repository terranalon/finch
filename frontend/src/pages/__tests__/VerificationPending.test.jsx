import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../contexts", () => ({
  useTheme: vi.fn(),
}));

vi.mock("../../lib/api", () => ({
  resendVerification: vi.fn(),
}));

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useLocation: () => ({
      state: { email: "user@example.com" },
    }),
  };
});

import { useTheme } from "../../contexts";
import { resendVerification } from "../../lib/api";
import VerificationPending from "../VerificationPending";

function renderPage() {
  return render(
    <MemoryRouter>
      <VerificationPending />
    </MemoryRouter>
  );
}

describe("VerificationPending", () => {
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

  it("renders the heading and email address", () => {
    renderPage();
    expect(screen.getByText("Check your email")).toBeInTheDocument();
    expect(screen.getByText("user@example.com")).toBeInTheDocument();
  });

  it("renders the resend button", () => {
    renderPage();
    expect(screen.getByRole("button", { name: /resend verification email/i })).toBeInTheDocument();
  });

  it("renders the sign-in link", () => {
    renderPage();
    expect(screen.getByRole("link", { name: /sign in/i })).toBeInTheDocument();
  });

  it("calls resendVerification on button click", async () => {
    resendVerification.mockResolvedValue({});
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /resend verification email/i }));

    await waitFor(() => {
      expect(resendVerification).toHaveBeenCalledWith("user@example.com");
    });
  });

  it("shows success message after resend", async () => {
    resendVerification.mockResolvedValue({});
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /resend verification email/i }));

    await waitFor(() => {
      expect(screen.getByText(/verification email sent/i)).toBeInTheDocument();
    });
  });
});
