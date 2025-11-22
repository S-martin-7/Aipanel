"use client";

import { useState, useEffect, useCallback } from "react";
import { documentsApi } from "@/lib/api";
import type { Document, SearchResult } from "@/types";

interface UseDocumentsOptions {
  agentId?: string;
  autoFetch?: boolean;
}

export function useDocuments(options: UseDocumentsOptions = { autoFetch: true }) {
  const { agentId, autoFetch } = options;
  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await documentsApi.list(agentId);
      setDocuments(data.documents);
      setTotal(data.total);
      return data;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Error al cargar documentos";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    if (autoFetch) {
      fetchDocuments();
    }
  }, [autoFetch, fetchDocuments]);

  const uploadDocument = useCallback(
    async (file: File, targetAgentId?: string): Promise<Document> => {
      setIsUploading(true);
      setUploadProgress(0);
      setError(null);
      try {
        // Simulate progress (actual progress would need XMLHttpRequest)
        const progressInterval = setInterval(() => {
          setUploadProgress((prev) => Math.min(prev + 10, 90));
        }, 200);

        const newDoc = await documentsApi.upload(file, targetAgentId || agentId || "");

        clearInterval(progressInterval);
        setUploadProgress(100);

        setDocuments((prev) => [...prev, newDoc]);
        setTotal((prev) => prev + 1);
        return newDoc;
      } catch (err: any) {
        const message = err.response?.data?.detail || "Error al subir documento";
        setError(message);
        throw err;
      } finally {
        setIsUploading(false);
        setTimeout(() => setUploadProgress(0), 1000);
      }
    },
    [agentId]
  );

  const deleteDocument = useCallback(async (id: string): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      await documentsApi.delete(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      setTotal((prev) => prev - 1);
    } catch (err: any) {
      const message = err.response?.data?.detail || "Error al eliminar documento";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    documents,
    total,
    isLoading,
    isUploading,
    uploadProgress,
    error,
    fetchDocuments,
    uploadDocument,
    deleteDocument,
  };
}

export function useDocumentSearch() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (query: string, agentId?: string) => {
    if (!query.trim()) {
      setResults([]);
      setTotal(0);
      return;
    }

    setIsSearching(true);
    setError(null);
    try {
      const data = await documentsApi.search(query, agentId);
      setResults(data.results);
      setTotal(data.total);
      return data;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Error en la busqueda";
      setError(message);
      throw err;
    } finally {
      setIsSearching(false);
    }
  }, []);

  const clearResults = useCallback(() => {
    setResults([]);
    setTotal(0);
  }, []);

  return {
    results,
    total,
    isSearching,
    error,
    search,
    clearResults,
  };
}
