"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, Plus, Settings, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { agentsApi } from "@/lib/api";

export default function AgentsPage() {
  const { data: agents, isLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agentes</h1>
          <p className="text-gray-500 mt-1">Gestiona tus agentes de IA</p>
        </div>
        <Button>
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Agente
        </Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="animate-pulse space-y-3">
                  <div className="h-10 w-10 bg-gray-200 rounded-lg" />
                  <div className="h-4 bg-gray-200 rounded w-3/4" />
                  <div className="h-3 bg-gray-200 rounded w-1/2" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : agents?.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Bot className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No tienes agentes</h3>
            <p className="text-sm text-gray-500 mt-1 mb-4">
              Crea tu primer agente para comenzar
            </p>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Crear Agente
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents?.map((agent) => (
            <Card key={agent.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                    <Bot className="w-5 h-5 text-primary-700" />
                  </div>
                  <div className="flex gap-1">
                    <button className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600">
                      <Settings className="w-4 h-4" />
                    </button>
                    <button className="p-1.5 hover:bg-red-50 rounded-lg text-gray-400 hover:text-red-600">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <h3 className="font-semibold text-gray-900 mt-4">{agent.name}</h3>
                <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                  {agent.description || "Sin descripción"}
                </p>
                <div className="flex items-center gap-2 mt-4">
                  <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full">
                    {agent.model}
                  </span>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    agent.status === "active"
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-600"
                  }`}>
                    {agent.status === "active" ? "Activo" : "Inactivo"}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
