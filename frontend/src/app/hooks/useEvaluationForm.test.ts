import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchCategories, fetchCompetitors } from "../api";
import { useEvaluationForm } from "./useEvaluationForm";

vi.mock("../api", () => ({
  fetchCategories: vi.fn(),
  fetchCompetitors: vi.fn(),
}));

const mockedFetchCategories = vi.mocked(fetchCategories);
const mockedFetchCompetitors = vi.mocked(fetchCompetitors);

/** The renderHook `.result` wrapper for the hook under test. */
type FormRender = { current: ReturnType<typeof useEvaluationForm> };

const CATEGORIES = ["project management", "issue tracking"];
const COMPETITORS = [{ name: "Jira", reason: "A project management rival" }];

/**
 * Drive the brand → category → competitors cascade to completion. Mocks must be
 * configured before calling this; any failed resolve leaves the hook mid-state
 * so callers can then assert the failure or retry.
 */
async function driveCascade(result: FormRender): Promise<void> {
  await act(async () => {
    result.current.setBrand("Linear");
  });
  await act(async () => {
    await result.current.resolveCategories();
  });
  await act(async () => {
    result.current.setCategory("project management");
  });
  await act(async () => {
    await result.current.resolveCompetitors();
  });
}

describe("useEvaluationForm", () => {
  beforeEach(() => {
    mockedFetchCategories.mockReset();
    mockedFetchCompetitors.mockReset();
  });

  it("treats an empty competitor list as a failed resolve: inline error, not ready", async () => {
    mockedFetchCategories.mockResolvedValue({ brand: "Linear", categories: CATEGORIES });
    // Backend contract is a 404, but a 200 + empty list must never silently block.
    mockedFetchCompetitors.mockResolvedValue({
      brand: "Linear",
      category: "project management",
      competitors: [],
    });

    const { result } = renderHook(() => useEvaluationForm());
    await driveCascade(result);

    expect(result.current.error).toBe("Could not resolve competitors for 'Linear'");
    expect(result.current.competitorsResolved).toBe(false);
    expect(result.current.competitors).toEqual([]);
    expect(result.current.isReady).toBe(false);
  });

  it("surfaces a 404/reject resolve as an inline error and not ready", async () => {
    mockedFetchCategories.mockResolvedValue({ brand: "Linear", categories: CATEGORIES });
    mockedFetchCompetitors.mockRejectedValue(
      new Error("Could not resolve competitors for 'Linear'"),
    );

    const { result } = renderHook(() => useEvaluationForm());
    await driveCascade(result);

    expect(result.current.error).toBe("Could not resolve competitors for 'Linear'");
    expect(result.current.competitorsResolved).toBe(false);
    expect(result.current.isReady).toBe(false);
  });

  it("Retry re-invokes the failed resolve and can succeed on the next attempt", async () => {
    mockedFetchCategories.mockResolvedValue({ brand: "Linear", categories: CATEGORIES });
    mockedFetchCompetitors
      .mockRejectedValueOnce(new Error("Could not resolve competitors for 'Linear'"))
      .mockResolvedValueOnce({
        brand: "Linear",
        category: "project management",
        competitors: COMPETITORS,
      });

    const { result } = renderHook(() => useEvaluationForm());
    await driveCascade(result);

    // First attempt failed loudly.
    expect(result.current.error).toBe("Could not resolve competitors for 'Linear'");
    expect(result.current.isReady).toBe(false);

    // Retry re-invokes the same resolve and recovers.
    await act(async () => {
      await result.current.resolveCompetitors();
    });

    expect(mockedFetchCompetitors).toHaveBeenCalledTimes(2);
    expect(result.current.error).toBeNull();
    expect(result.current.competitorsResolved).toBe(true);
    expect(result.current.competitors).toEqual(COMPETITORS);
    expect(result.current.isReady).toBe(true);
  });

  it("editing the brand past resolvedBrand clears the whole cascade and resets the step", async () => {
    mockedFetchCategories.mockResolvedValue({ brand: "Linear", categories: CATEGORIES });
    mockedFetchCompetitors.mockResolvedValue({
      brand: "Linear",
      category: "project management",
      competitors: COMPETITORS,
    });

    const { result } = renderHook(() => useEvaluationForm());
    await driveCascade(result);
    expect(result.current.isReady).toBe(true);

    await act(async () => {
      result.current.setBrand("Sony");
    });

    expect(result.current.brand).toBe("Sony");
    expect(result.current.categories).toEqual([]);
    expect(result.current.category).toBe("");
    expect(result.current.competitors).toEqual([]);
    expect(result.current.competitorsResolved).toBe(false);
    expect(result.current.resolvedBrand).toBeNull();
    expect(result.current.error).toBeNull();
    // Narrative resets to the brand step: nothing resolved yet.
    expect(result.current.isReady).toBe(false);
  });

  it("clears a stale inline step error when the brand changes (RR-7)", async () => {
    mockedFetchCategories.mockResolvedValue({ brand: "Linear", categories: CATEGORIES });
    mockedFetchCompetitors.mockRejectedValue(
      new Error("Could not resolve competitors for 'Linear'"),
    );

    const { result } = renderHook(() => useEvaluationForm());
    await driveCascade(result);
    expect(result.current.error).toBe("Could not resolve competitors for 'Linear'");

    await act(async () => {
      result.current.setBrand("Sony");
    });

    // The stale competitor error must not linger past its step.
    expect(result.current.error).toBeNull();
    expect(result.current.resolvedBrand).toBeNull();
    expect(result.current.isReady).toBe(false);
  });

  it("isReady gates on a full, non-empty cascade", async () => {
    const { result } = renderHook(() => useEvaluationForm());
    expect(result.current.isReady).toBe(false); // no brand yet

    await act(async () => {
      result.current.setBrand("Linear");
    });
    expect(result.current.isReady).toBe(false); // categories not resolved

    mockedFetchCategories.mockResolvedValue({ brand: "Linear", categories: CATEGORIES });
    await act(async () => {
      await result.current.resolveCategories();
    });
    expect(result.current.isReady).toBe(false); // no category chosen yet

    await act(async () => {
      result.current.setCategory("project management");
    });
    expect(result.current.isReady).toBe(false); // competitors not resolved

    mockedFetchCompetitors.mockResolvedValue({
      brand: "Linear",
      category: "project management",
      competitors: COMPETITORS,
    });
    await act(async () => {
      await result.current.resolveCompetitors();
    });
    expect(result.current.isReady).toBe(true); // full, non-empty cascade
  });
});
