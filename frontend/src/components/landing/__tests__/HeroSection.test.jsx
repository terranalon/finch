import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../../contexts", () => ({
  useAuth: vi.fn(),
}));

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useNavigate: () => mockNavigate };
});

import { useAuth } from "../../../contexts";
import HeroSection from "../HeroSection";

const mockLogin = vi.fn();

function renderHero() {
  return render(
    <MemoryRouter>
      <HeroSection />
    </MemoryRouter>
  );
}

describe("HeroSection", () => {
  beforeEach(() => {
    mockLogin.mockClear();
    mockNavigate.mockClear();
    useAuth.mockReturnValue({ login: mockLogin });
  });

  it("renders the Get Started Free link to /register", () => {
    renderHero();
    const link = screen.getByRole("link", { name: /get started free/i });
    expect(link).toHaveAttribute("href", "/register");
  });

  it("renders Try Demo button instead of See How It Works", () => {
    renderHero();
    expect(screen.getByRole("button", { name: /try demo/i })).toBeInTheDocument();
    expect(screen.queryByText(/see how it works/i)).not.toBeInTheDocument();
  });

  it("calls login with demo credentials when Try Demo is clicked", async () => {
    mockLogin.mockResolvedValue({});
    renderHero();

    fireEvent.click(screen.getByRole("button", { name: /try demo/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("demo@finch.com", "Demo1234");
      expect(mockNavigate).toHaveBeenCalledWith("/");
    });
  });

  it("navigates to /login if demo login fails", async () => {
    mockLogin.mockRejectedValue(new Error("fail"));
    renderHero();

    fireEvent.click(screen.getByRole("button", { name: /try demo/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/login");
    });
  });

  it("navigates to /login if demo account has MFA enabled", async () => {
    mockLogin.mockResolvedValue({ mfa_required: true });
    renderHero();

    fireEvent.click(screen.getByRole("button", { name: /try demo/i }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/login");
    });
  });

  it("renders the dashboard mockup", () => {
    renderHero();
    expect(screen.getByText("$247,832.15")).toBeInTheDocument();
  });
});
