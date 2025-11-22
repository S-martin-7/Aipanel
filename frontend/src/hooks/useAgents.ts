"use client";

import { useState, useEffect, useCallback } from "react";
import { agentsApi } from "@/lib/api";
import type { Agent } from "@/types";

interface UseAgentsOptions {
  autoFetch?: boolean;
}

export function useAgents(options: UseAgentsOptions = { autoFetch: true }) {
  const { autoFetch } = options;
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAgents = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await agentsApi.list();
      setAgents(data);
      return data;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Error al cargar agentes";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (autoFetch) {
      fetchAgents();
    }
  }, [autoFetch, fetchAgents]);

  const createAgent = useCallback(async (agentData: Partial<Agent>): Promise<Agent> => {
    setIsLoading(true);
    setError(null);
    try {
      const newAgent = await agentsApi.create(agentData);
      setAgents((prev) => [...prev, newAgent]);
      return newAgent;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Error al crear agente";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateAgent = useCallback(async (id: string, agentData: Partial<Agent>): Promise<Agent> => {
    setIsLoading(true);
    setError(null);
    try {
      const updatedAgent = await agentsApi.update(id, agentData);
      setAgents((prev) => prev.map((a) => (a.id === id ? updatedAgent : a)));
      return updatedAgent;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Error al actualizar agente";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const deleteAgent = useCallback(async (id: string): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      await agentsApi.delete(id);
      setAgents((prev) => prev.filter((a) => a.id !== id));
    } catch (err: any) {
      const message = err.response?.data?.detail || "Error al eliminar agente";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    agents,
    isLoading,
    error,
    fetchAgents,
    createAgent,
    updateAgent,
    deleteAgent,
  };
}

export function useAgent(id: string | null) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAgent = useCallback(async () => {
    if (!id) return null;
    setIsLoading(true);
    setError(null);
    try {
      const data = await agentsApi.get(id);
      setAgent(data);
      return data;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Error al cargar agente";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) {
      fetchAgent();
    }
  }, [id, fetchAgent]);

  return {
    agent,
    isLoading,
    error,
    refetch: fetchAgent,
  };
}
