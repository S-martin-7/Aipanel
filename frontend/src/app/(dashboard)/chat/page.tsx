"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bot, Plus, MessageSquare } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChatMessage } from "@/components/chat/chat-message";
import { ChatInput } from "@/components/chat/chat-input";
import { agentsApi, chatApi } from "@/lib/api";
import { useChatStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import type { Agent } from "@/types";

export default function ChatPage() {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const {
    currentAgent,
    messages,
    isStreaming,
    setCurrentAgent,
    addMessage,
    updateLastMessage,
    clearMessages,
    setIsStreaming,
  } = useChatStore();

  const { data: agents, isLoading: agentsLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list,
  });

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async (content: string) => {
    if (!currentAgent) return;

    // Add user message
    addMessage({ role: "user", content });

    // Add empty assistant message for streaming
    addMessage({ role: "assistant", content: "" });
    setIsStreaming(true);

    try {
      // Stream response
      for await (const chunk of chatApi.streamCompletion({
        agent_id: currentAgent.id,
        message: content,
      })) {
        updateLastMessage(chunk);
      }
    } catch (error) {
      console.error("Chat error:", error);
      updateLastMessage("\n\n*Error al obtener respuesta*");
    } finally {
      setIsStreaming(false);
    }
  };

  const handleSelectAgent = (agent: Agent) => {
    setCurrentAgent(agent);
    clearMessages();
  };

  const handleNewChat = () => {
    clearMessages();
  };

  return (
    <div className="h-[calc(100vh-7rem)] flex gap-4">
      {/* Agent Selector Sidebar */}
      <Card className="w-64 flex-shrink-0 flex flex-col">
        <div className="p-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Agentes</h2>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {agentsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-12 bg-gray-100 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : agents?.length === 0 ? (
            <div className="text-center py-8">
              <Bot className="w-10 h-10 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500">No hay agentes</p>
            </div>
          ) : (
            <div className="space-y-1">
              {agents?.map((agent) => (
                <button
                  key={agent.id}
                  onClick={() => handleSelectAgent(agent)}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors",
                    currentAgent?.id === agent.id
                      ? "bg-primary-50 text-primary-700"
                      : "hover:bg-gray-50 text-gray-700"
                  )}
                >
                  <Bot className="w-5 h-5 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{agent.name}</p>
                    <p className="text-xs text-gray-500 truncate">{agent.model}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* Chat Area */}
      <Card className="flex-1 flex flex-col overflow-hidden">
        {currentAgent ? (
          <>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                  <Bot className="w-5 h-5 text-primary-700" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">{currentAgent.name}</h3>
                  <p className="text-xs text-gray-500">{currentAgent.model}</p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={handleNewChat}>
                <Plus className="w-4 h-4 mr-1" />
                Nueva conversación
              </Button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center p-8">
                  <MessageSquare className="w-12 h-12 text-gray-300 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900">
                    Inicia una conversación
                  </h3>
                  <p className="text-sm text-gray-500 mt-1 max-w-sm">
                    Escribe un mensaje para comenzar a chatear con {currentAgent.name}
                  </p>
                </div>
              ) : (
                <div>
                  {messages.map((msg, idx) => (
                    <ChatMessage
                      key={idx}
                      role={msg.role as "user" | "assistant"}
                      content={msg.content}
                      isStreaming={isStreaming && idx === messages.length - 1 && msg.role === "assistant"}
                    />
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Input */}
            <ChatInput onSend={handleSendMessage} disabled={isStreaming} />
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <Bot className="w-16 h-16 text-gray-300 mb-4" />
            <h3 className="text-xl font-medium text-gray-900">
              Selecciona un agente
            </h3>
            <p className="text-sm text-gray-500 mt-2 max-w-sm">
              Elige un agente de la lista para comenzar una conversación
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
