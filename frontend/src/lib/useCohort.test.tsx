import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useCohort, useScenario } from "./useCohort";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

function Probe() {
  const [cohort, setCohort] = useCohort();
  const [scenario, setScenario] = useScenario();
  return (
    <div>
      <p>
        {cohort}/{scenario}
      </p>
      <button onClick={() => setCohort("portuguese")}>pt</button>
      <button onClick={() => setScenario("mid_year")}>mid</button>
    </div>
  );
}

describe("shared cohort and scenario", () => {
  it("defaults to Mathematics and the early scenario", () => {
    render(<Probe />);
    expect(screen.getByText("math/early")).toBeInTheDocument();
  });

  it("keeps the selection for the next page and writes it to the URL", () => {
    const { unmount } = render(<Probe />);
    fireEvent.click(screen.getByText("pt"));
    fireEvent.click(screen.getByText("mid"));
    expect(screen.getByText("portuguese/mid_year")).toBeInTheDocument();
    expect(window.location.search).toBe("?cohort=portuguese&scenario=mid_year");
    unmount();

    // A different page, without query parameters, starts from the shared choice.
    window.history.replaceState(null, "", "/eda");
    render(<Probe />);
    expect(screen.getByText("portuguese/mid_year")).toBeInTheDocument();
  });

  it("lets a shared link override the stored choice and ignores invalid values", () => {
    sessionStorage.setItem("saarps.cohort", "portuguese");
    window.history.replaceState(null, "", "/?cohort=math&scenario=bogus");
    render(<Probe />);
    expect(screen.getByText("math/early")).toBeInTheDocument();
    expect(sessionStorage.getItem("saarps.cohort")).toBe("math");
  });

  it("stores only the two selection strings", () => {
    render(<Probe />);
    fireEvent.click(screen.getByText("pt"));
    expect(Object.keys(sessionStorage)).toEqual(["saarps.cohort"]);
  });
});
