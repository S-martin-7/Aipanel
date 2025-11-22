"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, Upload, Trash2, Search } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { documentsApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function DocumentsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => documentsApi.list(),
  });

  const documents = data?.documents || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documentos</h1>
          <p className="text-gray-500 mt-1">Gestiona los documentos de tus agentes</p>
        </div>
        <Button>
          <Upload className="w-4 h-4 mr-2" />
          Subir Documento
        </Button>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Buscar en documentos..."
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Documents List */}
      <Card>
        <CardHeader>
          <CardTitle>Todos los documentos</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse flex items-center gap-4 p-3">
                  <div className="w-10 h-10 bg-gray-200 rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-1/3" />
                    <div className="h-3 bg-gray-200 rounded w-1/4" />
                  </div>
                </div>
              ))}
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900">No hay documentos</h3>
              <p className="text-sm text-gray-500 mt-1">
                Sube tu primer documento para comenzar
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {documents.map((doc) => (
                <div key={doc.id} className="flex items-center gap-4 p-3 hover:bg-gray-50 rounded-lg">
                  <div className="w-10 h-10 bg-primary-50 rounded-lg flex items-center justify-center">
                    <FileText className="w-5 h-5 text-primary-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{doc.filename}</p>
                    <p className="text-sm text-gray-500">
                      {doc.chunk_count} chunks &middot; {formatDate(doc.created_at)}
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    doc.status === "completed"
                      ? "bg-green-100 text-green-700"
                      : doc.status === "processing"
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-gray-100 text-gray-600"
                  }`}>
                    {doc.status === "completed" ? "Procesado" : doc.status === "processing" ? "Procesando" : doc.status}
                  </span>
                  <button className="p-1.5 hover:bg-red-50 rounded-lg text-gray-400 hover:text-red-600">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
