import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import AuthSwitchRoute from "../AuthSwitchRoute";

// Mock the useAuth hook
vi.mock("../../contexts", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "../../contexts";

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("AuthSwitchRoute", () => {
  it("renders unauthenticated content when not logged in", () => {
    useAuth.mockReturnValue({ isAuthenticated: false, loading: false });

    renderWithRouter(
      <AuthSwitchRoute
        authenticated={<div>Dashboard</div>}
        unauthenticated={<div>Landing</div>}
      />
    );

    expect(screen.getByText("Landing")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard")).not.toBeInTheDocument();
  });

  it("renders authenticated content when logged in", () => {
    useAuth.mockReturnValue({ isAuthenticated: true, loading: false });

    renderWithRouter(
      <AuthSwitchRoute
        authenticated={<div>Dashboard</div>}
        unauthenticated={<div>Landing</div>}
      />
    );

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.queryByText("Landing")).not.toBeInTheDocument();
  });

  it("renders loading spinner while auth state resolves", () => {
    useAuth.mockReturnValue({ isAuthenticated: false, loading: true });

    const { container } = renderWithRouter(
      <AuthSwitchRoute
        authenticated={<div>Dashboard</div>}
        unauthenticated={<div>Landing</div>}
      />
    );

    expect(screen.queryByText("Dashboard")).not.toBeInTheDocument();
    expect(screen.queryByText("Landing")).not.toBeInTheDocument();
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });
});
