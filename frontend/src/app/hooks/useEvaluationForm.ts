import { useCallback, useMemo, useState } from "react";
import { fetchCategories, fetchCompetitors } from "../api";
import type { Competitor, EvaluateRequest } from "../types";

export interface UseEvaluationForm {
  brand: string;
  category: string;
  categories: string[];
  competitors: Competitor[];
  resolvedBrand: string | null;
  competitorsResolved: boolean;
  resolvingCategories: boolean;
  resolvingCompetitors: boolean;
  error: string | null;
  setBrand: (value: string) => void;
  setCategory: (value: string) => void;
  resolveCategories: () => Promise<void>;
  resolveCompetitors: () => Promise<void>;
  /** True when every field is resolved and an evaluation could be launched. */
  isReady: boolean;
  /** The request the current form describes, or null when it is incomplete. */
  buildRequest: () => EvaluateRequest | null;
}

/**
 * The brand -> category -> competitors cascade.
 *
 * Each step is resolved by Gemini and feeds the next, so any change upstream
 * invalidates everything downstream: a new brand discards its categories, and
 * a new category discards its competitors. Without that, the form would let
 * you launch an evaluation pairing one brand's name with another's rivals.
 */
export function useEvaluationForm(): UseEvaluationForm {
  const [brand, setBrandState] = useState("");
  const [category, setCategoryState] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [resolvedBrand, setResolvedBrand] = useState<string | null>(null);
  const [competitorsResolved, setCompetitorsResolved] = useState(false);
  const [resolvingCategories, setResolvingCategories] = useState(false);
  const [resolvingCompetitors, setResolvingCompetitors] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setBrand = useCallback(
    (value: string) => {
      setBrandState(value);
      // Typing past the resolved brand invalidates the whole cascade, and a
      // stale inline step error for the old brand must not linger.
      if (value !== resolvedBrand) {
        setCategories([]);
        setCategoryState("");
        setCompetitors([]);
        setCompetitorsResolved(false);
        setResolvedBrand(null);
        setError(null);
      }
    },
    [resolvedBrand],
  );

  const setCategory = useCallback((value: string) => {
    setCategoryState(value);
    setCompetitors([]);
    setCompetitorsResolved(false);
    // A new category invalidates the previous competitors resolve — drop its
    // stale error too.
    setError(null);
  }, []);

  const resolveCategories = useCallback(async () => {
    const trimmed = brand.trim();
    if (!trimmed) return;
    // Already resolved for this exact brand — don't spend a Gemini call on blur.
    if (resolvedBrand === trimmed && categories.length > 0) return;

    try {
      setResolvingCategories(true);
      setError(null);
      setCategoryState("");
      setCompetitors([]);
      setCompetitorsResolved(false);
      const data = await fetchCategories(trimmed);
      setCategories(data.categories);
      setResolvedBrand(trimmed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to resolve categories");
      setCategories([]);
      setResolvedBrand(null);
    } finally {
      setResolvingCategories(false);
    }
  }, [brand, resolvedBrand, categories.length]);

  const resolveCompetitors = useCallback(async () => {
    if (!category || !resolvedBrand) return;

    try {
      setResolvingCompetitors(true);
      setError(null);
      const data = await fetchCompetitors(resolvedBrand, category);
      if (data.competitors.length === 0) {
        // Defensive alongside the backend 404: a 200+empty response must never
        // silently block with Run disabled and no explanation.
        setCompetitors([]);
        setCompetitorsResolved(false);
        setError(`Could not resolve competitors for '${resolvedBrand}'`);
        return;
      }
      setCompetitors(data.competitors);
      setCompetitorsResolved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to resolve competitors");
      setCompetitors([]);
      setCompetitorsResolved(false);
    } finally {
      setResolvingCompetitors(false);
    }
  }, [category, resolvedBrand]);

  const isReady = useMemo(
    () =>
      brand.trim() !== "" &&
      category !== "" &&
      competitorsResolved &&
      competitors.length > 0 &&
      !resolvingCategories &&
      !resolvingCompetitors,
    [
      brand,
      category,
      competitorsResolved,
      competitors.length,
      resolvingCategories,
      resolvingCompetitors,
    ],
  );

  const buildRequest = useCallback((): EvaluateRequest | null => {
    const trimmed = brand.trim();
    if (!trimmed || !category || competitors.length === 0) return null;
    return {
      brand: trimmed,
      category,
      competitors: competitors.map((c) => c.name),
    };
  }, [brand, category, competitors]);

  return {
    brand,
    category,
    categories,
    competitors,
    resolvedBrand,
    competitorsResolved,
    resolvingCategories,
    resolvingCompetitors,
    error,
    setBrand,
    setCategory,
    resolveCategories,
    resolveCompetitors,
    isReady,
    buildRequest,
  };
}
