import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../contexts", () => ({
  useAuth: vi.fn(),
  useTheme: vi.fn(),
}));

vi.mock("../../lib/api", () => ({
  verifyMfa: vi.fn(),
  sendMfaEmailCode: vi.fn(),
}));

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({
      state: {
        tempToken: "test-temp-token",
        methods: ["totp"],
        primaryMethod: "totp",
      },
    }),
  };
});

import { useAuth, useTheme } from "../../contexts";
import { verifyMfa } from "../../lib/api";
import MfaVerify from "../MfaVerify";

function renderMfaVerify() {
  return render(
    <MemoryRouter>
      <MfaVerify />
    </MemoryRouter>
  );
}

describe("MfaVerify", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ setUserFromMfa: vi.fn() });
    useTheme.mockReturnValue({ theme: "light", setTheme: vi.fn() });
  });

  it("renders inside AuthLayout with split-panel branding", () => {
    renderMfaVerify();
    expect(screen.getByText("$247,832.15")).toBeInTheDocument();
  });

  it("does not render a ThemeToggle", () => {
    renderMfaVerify();
    expect(screen.queryByTitle(/toggle theme/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/toggle.*theme/i)).not.toBeInTheDocument();
  });

  it("renders the heading and code input", () => {
    renderMfaVerify();
    expect(screen.getByText("Two-factor authentication")).toBeInTheDocument();
    expect(screen.getByLabelText(/authenticator code/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /verify/i })).toBeInTheDocument();
  });

  it("renders back-to-login link", () => {
    renderMfaVerify();
    expect(screen.getByText(/back to sign in/i)).toBeInTheDocument();
  });

  it("renders recovery code option", () => {
    renderMfaVerify();
    expect(screen.getByText(/use a recovery code/i)).toBeInTheDocument();
  });

  it("does not show method selector when only one method available", () => {
    renderMfaVerify();
    expect(screen.queryByText(/verification method/i)).not.toBeInTheDocument();
  });

  it("calls verifyMfa and navigates on successful submit", async () => {
    const mockSetUser = vi.fn();
    useAuth.mockReturnValue({ setUserFromMfa: mockSetUser });
    verifyMfa.mockResolvedValue({ user: { id: 1 } });
    renderMfaVerify();

    fireEvent.change(screen.getByLabelText(/authenticator code/i), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByRole("button", { name: /verify/i }));

    await waitFor(() => {
      expect(verifyMfa).toHaveBeenCalledWith("test-temp-token", "123456", "totp");
      expect(mockSetUser).toHaveBeenCalledWith({ id: 1 });
      expect(mockNavigate).toHaveBeenCalledWith("/");
    });
  });

  it("shows error on verification failure", async () => {
    verifyMfa.mockRejectedValue(new Error("Invalid code"));
    renderMfaVerify();

    fireEvent.change(screen.getByLabelText(/authenticator code/i), {
      target: { value: "000000" },
    });
    fireEvent.click(screen.getByRole("button", { name: /verify/i }));

    await waitFor(() => {
      expect(screen.getByText("Invalid code")).toBeInTheDocument();
    });
  });
});
