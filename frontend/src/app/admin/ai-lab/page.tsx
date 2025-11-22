"use client";

import React from "react";
import { Send, Settings, RefreshCw, Trash2, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";

interface Model {
  id: string;
  name: string;
  provider: string;
  status: "stable" | "experimental" | "deprecated";
  inputCost: number;
  outputCost: number;
  maxTokens: number;
  capabilities: string[];
}

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

const models: Model[] = [
  {
    id: "gpt-4o",
    name: "GPT-4o",
    provider: "OpenAI",
    status: "stable",
    inputCost: 2.5,
    outputCost: 10,
    maxTokens: 128000,
    capabilities: ["chat", "vision", "streaming"],
  },
  {
    id: "gpt-4o-mini",
    name: "GPT-4o Mini",
    provider: "OpenAI",
    status: "stable",
    inputCost: 0.15,
    outputCost: 0.6,
    maxTokens: 128000,
    capabilities: ["chat", "streaming"],
  },
  {
    id: "claude-sonnet-4-5",
    name: "Claude Sonnet 4.5",
    provider: "Anthropic",
    status: "stable",
    inputCost: 3,
    outputCost: 15,
    maxTokens: 200000,
    capabilities: ["chat", "vision", "streaming"],
  },
  {
    id: "claude-haiku-3-5",
    name: "Claude Haiku 3.5",
    provider: "Anthropic",
    status: "stable",
    inputCost: 0.25,
    outputCost: 1.25,
    maxTokens: 200000,
    capabilities: ["chat", "streaming"],
  },
  {
    id: "o3-mini",
    name: "O3 Mini",
    provider: "OpenAI",
    status: "experimental",
    inputCost: 1.1,
    outputCost: 4.4,
    maxTokens: 128000,
    capabilities: ["chat", "reasoning", "streaming"],
  },
];

export default function AILabPage() {
  const [selectedModel, setSelectedModel] = React.useState(models[0].id);
  const [systemPrompt, setSystemPrompt] = React.useState(
    "Eres un asistente útil y amigable."
  );
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [temperature, setTemperature] = React.useState(0.7);
  const [maxTokens, setMaxTokens] = React.useState(1000);
  const [copied, setCopied] = React.useState(false);

  const model = models.find((m) => m.id === selectedModel)!;

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    // Simulate API call
    setTimeout(() => {
      const assistantMessage: Message = {
        role: "assistant",
        content: `Esta es una respuesta simulada del modelo ${model.name}. En producción, esto se conectaría a la API real.\n\nTu mensaje fue: "${userMessage.content}"`,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setLoading(false);
    }, 1500);
  };

  const handleClear = () => {
    setMessages([]);
  };

  const handleCopyConversation = () => {
    const text = messages
      .map((m) => `${m.role === "user" ? "Usuario" : "Asistente"}: ${m.content}`)
      .join("\n\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">AI Lab</h2>
          <p className="text-muted-foreground">
            Prueba y compara modelos de AI antes de habilitarlos en producción
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Settings Panel */}
        <Card className="p-4 lg:col-span-1">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Settings className="h-4 w-4" /> Configuración
          </h3>

          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Modelo</label>
              <Select value={selectedModel} onValueChange={setSelectedModel}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {models.map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      <div className="flex items-center gap-2">
                        {m.name}
                        <Badge
                          variant={
                            m.status === "stable"
                              ? "success"
                              : m.status === "experimental"
                              ? "warning"
                              : "secondary"
                          }
                          className="text-xs"
                        >
                          {m.status}
                        </Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Model info */}
            <div className="rounded-lg bg-muted p-3 text-sm space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Proveedor</span>
                <span className="font-medium">{model.provider}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Input</span>
                <span className="font-medium">${model.inputCost}/1M</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Output</span>
                <span className="font-medium">${model.outputCost}/1M</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Max Tokens</span>
                <span className="font-medium">{model.maxTokens.toLocaleString()}</span>
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {model.capabilities.map((cap) => (
                  <Badge key={cap} variant="outline" className="text-xs">
                    {cap}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">System Prompt</label>
              <Textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                rows={4}
                placeholder="Instrucciones para el modelo..."
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">
                Temperature: {temperature}
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">
                Max Tokens: {maxTokens}
              </label>
              <input
                type="range"
                min="100"
                max="4000"
                step="100"
                value={maxTokens}
                onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                className="w-full"
              />
            </div>
          </div>
        </Card>

        {/* Chat Panel */}
        <Card className="p-4 lg:col-span-2 flex flex-col h-[600px]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Conversación</h3>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyConversation}
                disabled={messages.length === 0}
              >
                {copied ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleClear}
                disabled={messages.length === 0}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-4 mb-4">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <p>Envía un mensaje para comenzar la conversación</p>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2 ${
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-lg px-4 py-2 flex items-center gap-2">
                  <Spinner size="sm" />
                  <span className="text-sm text-muted-foreground">
                    Generando respuesta...
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="flex gap-2">
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
            />
            <Button onClick={handleSend} disabled={loading || !input.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </Card>
      </div>

      {/* Models Comparison Table */}
      <Card className="p-6">
        <h3 className="font-semibold mb-4">Comparación de Modelos</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">Modelo</th>
                <th className="text-left py-2">Proveedor</th>
                <th className="text-left py-2">Estado</th>
                <th className="text-right py-2">Input $/1M</th>
                <th className="text-right py-2">Output $/1M</th>
                <th className="text-right py-2">Max Tokens</th>
                <th className="text-left py-2">Capacidades</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.id} className="border-b">
                  <td className="py-2 font-medium">{m.name}</td>
                  <td className="py-2">{m.provider}</td>
                  <td className="py-2">
                    <Badge
                      variant={
                        m.status === "stable"
                          ? "success"
                          : m.status === "experimental"
                          ? "warning"
                          : "secondary"
                      }
                    >
                      {m.status}
                    </Badge>
                  </td>
                  <td className="py-2 text-right">${m.inputCost}</td>
                  <td className="py-2 text-right">${m.outputCost}</td>
                  <td className="py-2 text-right">{m.maxTokens.toLocaleString()}</td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-1">
                      {m.capabilities.map((cap) => (
                        <Badge key={cap} variant="outline" className="text-xs">
                          {cap}
                        </Badge>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
