"use client";

import React from "react";
import { Send, Settings, Trash2, Copy, Check, Paperclip, Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";

interface Agent {
  id: string;
  name: string;
  model: string;
  description: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  tokens?: { input: number; output: number };
}

// Mock agents
const agents: Agent[] = [
  { id: "1", name: "Asistente General", model: "gpt-4o-mini", description: "Asistente para consultas generales" },
  { id: "2", name: "Soporte Técnico", model: "gpt-4o", description: "Especializado en soporte técnico" },
  { id: "3", name: "Ventas", model: "claude-sonnet-4-5", description: "Agente de ventas y cotizaciones" },
];

export default function PlaygroundPage() {
  const [selectedAgent, setSelectedAgent] = React.useState(agents[0].id);
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [streaming, setStreaming] = React.useState(false);
  const [copied, setCopied] = React.useState(false);
  const [showSettings, setShowSettings] = React.useState(false);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  const agent = agents.find((a) => a.id === selectedAgent)!;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setStreaming(true);

    // Simulate streaming response
    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: "",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, assistantMessage]);

    const responseText = `Esta es una respuesta del agente "${agent.name}" usando el modelo ${agent.model}.\n\nTu consulta fue: "${userMessage.content}"\n\nEn producción, esta respuesta vendría en streaming desde la API real, mostrando cada token a medida que se genera.`;

    // Simulate streaming
    let currentIndex = 0;
    const streamInterval = setInterval(() => {
      if (currentIndex < responseText.length) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessage.id
              ? { ...m, content: responseText.slice(0, currentIndex + 5) }
              : m
          )
        );
        currentIndex += 5;
      } else {
        clearInterval(streamInterval);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessage.id
              ? {
                  ...m,
                  content: responseText,
                  tokens: { input: 45, output: 82 },
                }
              : m
          )
        );
        setLoading(false);
        setStreaming(false);
      }
    }, 30);
  };

  const handleClear = () => {
    setMessages([]);
  };

  const handleCopy = () => {
    const text = messages
      .map((m) => `${m.role === "user" ? "Tú" : agent.name}: ${m.content}`)
      .join("\n\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const totalTokens = messages.reduce(
    (acc, m) => ({
      input: acc.input + (m.tokens?.input || 0),
      output: acc.output + (m.tokens?.output || 0),
    }),
    { input: 0, output: 0 }
  );

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Playground</h2>
          <p className="text-muted-foreground">
            Prueba tus agentes en un entorno interactivo
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Select value={selectedAgent} onValueChange={setSelectedAgent}>
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {agents.map((a) => (
                <SelectItem key={a.id} value={a.id}>
                  {a.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSettings(!showSettings)}
          >
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex-1 flex gap-4 overflow-hidden">
        {/* Chat Area */}
        <Card className="flex-1 flex flex-col">
          {/* Agent Info */}
          <div className="p-4 border-b flex items-center justify-between">
            <div>
              <h3 className="font-semibold">{agent.name}</h3>
              <p className="text-sm text-muted-foreground">{agent.description}</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline">{agent.model}</Badge>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                disabled={messages.length === 0}
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClear}
                disabled={messages.length === 0}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <h3 className="font-medium mb-2">¡Comienza una conversación!</h3>
                  <p className="text-sm text-muted-foreground">
                    Escribe un mensaje para probar el agente {agent.name}
                  </p>
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-3 ${
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    {message.role === "assistant" && streaming && !message.tokens && (
                      <span className="inline-block w-2 h-4 bg-current animate-pulse ml-1" />
                    )}
                    {message.tokens && (
                      <p className="text-xs mt-2 opacity-70">
                        {message.tokens.input} input + {message.tokens.output} output tokens
                      </p>
                    )}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t">
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" disabled>
                <Paperclip className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" disabled>
                <Mic className="h-4 w-4" />
              </Button>
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Escribe tu mensaje..."
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                disabled={loading}
                className="flex-1"
              />
              <Button onClick={handleSend} disabled={loading || !input.trim()}>
                {loading ? <Spinner size="sm" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
            <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
              <span>
                Tokens usados: {totalTokens.input + totalTokens.output} (
                {totalTokens.input} in / {totalTokens.output} out)
              </span>
              <span>Enter para enviar</span>
            </div>
          </div>
        </Card>

        {/* Settings Panel */}
        {showSettings && (
          <Card className="w-80 p-4 overflow-y-auto">
            <h3 className="font-semibold mb-4">Configuración</h3>
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Temperature</label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  defaultValue="0.7"
                  className="w-full"
                />
                <p className="text-xs text-muted-foreground">
                  Controla la creatividad de las respuestas
                </p>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Max Tokens</label>
                <Input type="number" defaultValue="1000" />
                <p className="text-xs text-muted-foreground">
                  Límite de tokens en la respuesta
                </p>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">System Prompt</label>
                <Textarea
                  rows={6}
                  defaultValue="Eres un asistente útil y amigable."
                  className="text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="streaming" defaultChecked />
                <label htmlFor="streaming" className="text-sm">
                  Habilitar streaming
                </label>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="context" defaultChecked />
                <label htmlFor="context" className="text-sm">
                  Usar contexto de documentos
                </label>
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
