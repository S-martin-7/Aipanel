"use client";

import { useState, useEffect, useCallback } from "react";
import { usageApi } from "@/lib/api";
import type { UsageQuota, UsageSummary } from "@/types";

interface UseUsageOptions {
  autoFetch?: boolean;
  refreshInterval?: number; // in milliseconds
}

export function useUsage(options: UseUsageOptions = { autoFetch: true }) {
  const { autoFetch, refreshInterval } = options;
  const [quota, setQuota] = useState<UsageQuota | null>(null);
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [chartData, setChartData] = useState<{ date: string; tokens: number; requests: number }[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchQuota = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await usageApi.getQuota();
      setQuota(data);
      return data;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Error al cargar cuota";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchSummary = useCallback(async (period?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await usageApi.getSummary(period);
      setSummary(data);
      return data;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Error al cargar resumen";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchChartData = useCallback(async (days = 30) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await usageApi.getChart(days);
      setChartData(data.data_points);
      return data.data_points;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Error al cargar grafico";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchAll = useCallback(async () => {
    await Promise.all([fetchQuota(), fetchSummary(), fetchChartData()]);
  }, [fetchQuota, fetchSummary, fetchChartData]);

  useEffect(() => {
    if (autoFetch) {
      fetchAll();
    }
  }, [autoFetch, fetchAll]);

  // Optional auto-refresh
  useEffect(() => {
    if (!refreshInterval) return;

    const interval = setInterval(() => {
      fetchQuota();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval, fetchQuota]);

  // Calculate usage percentage
  const usagePercentage = quota
    ? Math.round((quota.tokens_used / quota.tokens_limit) * 100)
    : 0;

  // Determine alert level
  const alertLevel: "ok" | "warning" | "critical" = usagePercentage >= 90
    ? "critical"
    : usagePercentage >= 75
      ? "warning"
      : "ok";

  return {
    quota,
    summary,
    chartData,
    usagePercentage,
    alertLevel,
    isLoading,
    error,
    fetchQuota,
    fetchSummary,
    fetchChartData,
    refetch: fetchAll,
  };
}

// Hook for usage alerts
export function useUsageAlert(threshold = 75) {
  const { usagePercentage, alertLevel } = useUsage({ autoFetch: true, refreshInterval: 60000 });
  const [dismissed, setDismissed] = useState(false);

  const showAlert = usagePercentage >= threshold && !dismissed;

  const dismissAlert = useCallback(() => {
    setDismissed(true);
    // Reset after 1 hour
    setTimeout(() => setDismissed(false), 3600000);
  }, []);

  return {
    showAlert,
    usagePercentage,
    alertLevel,
    dismissAlert,
  };
}
