"use client";

import { useState, useEffect } from "react";
import {
  Webhook,
  Plus,
  Trash2,
  RefreshCw,
  CheckCircle,
  XCircle,
  Eye,
  Copy,
  RotateCw,
  Clock,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

// Types
interface WebhookConfig {
  id: string;
  url: string;
  events: string[];
  secret: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

interface WebhookDelivery {
  id: string;
  event: string;
  status: "pending" | "delivered" | "failed";
  response_code?: number;
  delivered_at?: string;
  error?: string;
  attempts: number;
}

const WEBHOOK_EVENTS = [
  { value: "chat.message", label: "Mensaje de chat", description: "Cuando se recibe o envia un mensaje" },
  { value: "chat.conversation.created", label: "Conversacion creada", description: "Cuando se inicia una conversacion" },
  { value: "chat.conversation.deleted", label: "Conversacion eliminada", description: "Cuando se elimina una conversacion" },
  { value: "document.uploaded", label: "Documento subido", description: "Cuando se sube un documento" },
  { value: "document.processed", label: "Documento procesado", description: "Cuando se procesa un documento" },
  { value: "document.deleted", label: "Documento eliminado", description: "Cuando se elimina un documento" },
  { value: "agent.created", label: "Agente creado", description: "Cuando se crea un agente" },
  { value: "agent.updated", label: "Agente actualizado", description: "Cuando se actualiza un agente" },
  { value: "agent.deleted", label: "Agente eliminado", description: "Cuando se elimina un agente" },
  { value: "usage.threshold.warning", label: "Alerta de uso", description: "Cuando se alcanza 80% del limite" },
  { value: "usage.threshold.critical", label: "Uso critico", description: "Cuando se alcanza 95% del limite" },
  { value: "payment.success", label: "Pago exitoso", description: "Cuando se completa un pago" },
  { value: "payment.failed", label: "Pago fallido", description: "Cuando falla un pago" },
];

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<WebhookConfig[]>([]);
  const [deliveries, setDeliveries] = useState<{ [key: string]: WebhookDelivery[] }>({});
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedWebhook, setSelectedWebhook] = useState<string | null>(null);
  const [showSecret, setShowSecret] = useState<string | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    url: "",
    events: [] as string[],
  });

  useEffect(() => {
    loadWebhooks();
  }, []);

  const loadWebhooks = async () => {
    try {
      setLoading(true);
      const response = await api.get("/webhooks");
      setWebhooks(response || []);
    } catch (error) {
      console.error("Error loading webhooks:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadDeliveries = async (webhookId: string) => {
    try {
      const response = await api.get(`/webhooks/${webhookId}/deliveries`);
      setDeliveries((prev) => ({ ...prev, [webhookId]: response || [] }));
    } catch (error) {
      console.error("Error loading deliveries:", error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.events.length === 0) {
      alert("Selecciona al menos un evento");
      return;
    }
    try {
      await api.post("/webhooks", formData);
      setShowForm(false);
      setFormData({ url: "", events: [] });
      loadWebhooks();
    } catch (error) {
      console.error("Error creating webhook:", error);
      alert("Error al crear el webhook");
    }
  };

  const handleDelete = async (webhookId: string) => {
    if (!confirm("Estas seguro de eliminar este webhook?")) return;
    try {
      await api.delete(`/webhooks/${webhookId}`);
      loadWebhooks();
    } catch (error) {
      console.error("Error deleting webhook:", error);
    }
  };

  const toggleActive = async (webhook: WebhookConfig) => {
    try {
      await api.patch(`/webhooks/${webhook.id}`, {
        is_active: !webhook.is_active,
      });
      loadWebhooks();
    } catch (error) {
      console.error("Error toggling webhook:", error);
    }
  };

  const handleRetry = async (webhookId: string, deliveryId: string) => {
    try {
      setRetrying(deliveryId);
      await api.post(`/webhooks/${webhookId}/deliveries/${deliveryId}/retry`);
      loadDeliveries(webhookId);
    } catch (error) {
      console.error("Error retrying delivery:", error);
    } finally {
      setRetrying(null);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert("Copiado al portapapeles");
  };

  const toggleEvent = (event: string) => {
    setFormData((prev) => ({
      ...prev,
      events: prev.events.includes(event)
        ? prev.events.filter((e) => e !== event)
        : [...prev.events, event],
    }));
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "delivered":
        return <Badge variant="success">Entregado</Badge>;
      case "failed":
        return <Badge variant="destructive">Fallido</Badge>;
      default:
        return <Badge variant="secondary">Pendiente</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Webhooks</h1>
          <p className="text-gray-500 mt-1">
            Recibe notificaciones en tiempo real cuando ocurren eventos en tu cuenta
          </p>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Agregar Webhook
        </Button>
      </div>

      {/* Add Form */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>Nuevo Webhook</CardTitle>
            <CardDescription>
              Configura una URL para recibir notificaciones de eventos
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <Input
                label="URL del Webhook"
                type="url"
                value={formData.url}
                onChange={(e) =>
                  setFormData({ ...formData, url: e.target.value })
                }
                placeholder="https://tu-servidor.com/webhook"
                required
              />

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Eventos a recibir
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {WEBHOOK_EVENTS.map((event) => (
                    <label
                      key={event.value}
                      className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                        formData.events.includes(event.value)
                          ? "border-primary-500 bg-primary-50"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={formData.events.includes(event.value)}
                        onChange={() => toggleEvent(event.value)}
                        className="mt-1 mr-3"
                      />
                      <div>
                        <span className="text-sm font-medium text-gray-900">
                          {event.label}
                        </span>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {event.description}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex gap-3">
                <Button type="submit">Crear Webhook</Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowForm(false)}
                >
                  Cancelar
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Webhooks List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Webhook className="w-5 h-5" />
            Webhooks Configurados
          </CardTitle>
          <CardDescription>
            Gestiona tus endpoints de webhook
          </CardDescription>
        </CardHeader>
        <CardContent>
          {webhooks.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Webhook className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>No tienes webhooks configurados</p>
              <p className="text-sm mt-1">
                Crea un webhook para recibir eventos en tiempo real
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {webhooks.map((webhook) => (
                <div
                  key={webhook.id}
                  className={`border rounded-lg overflow-hidden ${
                    webhook.is_active
                      ? "border-green-200"
                      : "border-gray-200"
                  }`}
                >
                  <div
                    className={`p-4 ${
                      webhook.is_active ? "bg-green-50" : "bg-gray-50"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <code className="text-sm font-mono text-gray-900 bg-white px-2 py-1 rounded border">
                            {webhook.url}
                          </code>
                          {webhook.is_active ? (
                            <CheckCircle className="w-4 h-4 text-green-600" />
                          ) : (
                            <XCircle className="w-4 h-4 text-gray-400" />
                          )}
                        </div>

                        <div className="flex flex-wrap gap-1 mt-3">
                          {webhook.events.map((event) => (
                            <Badge key={event} variant="secondary" className="text-xs">
                              {event}
                            </Badge>
                          ))}
                        </div>

                        <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                          <div className="flex items-center gap-1">
                            <span>Secret:</span>
                            <code className="font-mono bg-gray-100 px-1 rounded">
                              {showSecret === webhook.id
                                ? webhook.secret
                                : "whsec_••••••••"}
                            </code>
                            <button
                              onClick={() =>
                                setShowSecret(
                                  showSecret === webhook.id ? null : webhook.id
                                )
                              }
                              className="text-gray-400 hover:text-gray-600"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => copyToClipboard(webhook.secret)}
                              className="text-gray-400 hover:text-gray-600"
                            >
                              <Copy className="w-4 h-4" />
                            </button>
                          </div>
                        </div>

                        <p className="text-xs text-gray-400 mt-2">
                          Creado: {new Date(webhook.created_at).toLocaleString()}
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            if (selectedWebhook === webhook.id) {
                              setSelectedWebhook(null);
                            } else {
                              setSelectedWebhook(webhook.id);
                              loadDeliveries(webhook.id);
                            }
                          }}
                        >
                          <Clock className="w-4 h-4 mr-1" />
                          Historial
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleActive(webhook)}
                        >
                          {webhook.is_active ? "Desactivar" : "Activar"}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(webhook.id)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>

                  {/* Deliveries History */}
                  {selectedWebhook === webhook.id && (
                    <div className="border-t bg-white p-4">
                      <h4 className="text-sm font-medium text-gray-700 mb-3">
                        Historial de Entregas
                      </h4>
                      {deliveries[webhook.id]?.length > 0 ? (
                        <div className="space-y-2">
                          {deliveries[webhook.id].map((delivery) => (
                            <div
                              key={delivery.id}
                              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                            >
                              <div className="flex items-center gap-3">
                                {getStatusBadge(delivery.status)}
                                <span className="text-sm font-medium">
                                  {delivery.event}
                                </span>
                                {delivery.response_code && (
                                  <span className="text-xs text-gray-500">
                                    HTTP {delivery.response_code}
                                  </span>
                                )}
                                {delivery.error && (
                                  <span className="text-xs text-red-500 flex items-center gap-1">
                                    <AlertCircle className="w-3 h-3" />
                                    {delivery.error}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-gray-400">
                                  {delivery.delivered_at
                                    ? new Date(delivery.delivered_at).toLocaleString()
                                    : `Intentos: ${delivery.attempts}`}
                                </span>
                                {delivery.status === "failed" && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() =>
                                      handleRetry(webhook.id, delivery.id)
                                    }
                                    disabled={retrying === delivery.id}
                                  >
                                    <RotateCw
                                      className={`w-4 h-4 ${
                                        retrying === delivery.id
                                          ? "animate-spin"
                                          : ""
                                      }`}
                                    />
                                  </Button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500 text-center py-4">
                          No hay entregas registradas
                        </p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Documentation */}
      <Card>
        <CardHeader>
          <CardTitle>Verificacion de Firmas</CardTitle>
        </CardHeader>
        <CardContent className="prose prose-sm max-w-none">
          <p className="text-gray-600">
            Todas las peticiones webhook incluyen una firma HMAC-SHA256 en el header{" "}
            <code className="bg-gray-100 px-1 rounded">X-Webhook-Signature</code>.
          </p>
          <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg text-xs overflow-x-auto mt-4">
{`// Ejemplo de verificacion en Node.js
const crypto = require('crypto');

function verifyWebhook(payload, signature, secret) {
  const timestamp = signature.split(',')[0].split('=')[1];
  const sig = signature.split(',')[1].split('=')[1];

  const signedPayload = \`\${timestamp}.\${JSON.stringify(payload)}\`;
  const expectedSig = crypto
    .createHmac('sha256', secret)
    .update(signedPayload)
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(sig),
    Buffer.from(expectedSig)
  );
}`}
          </pre>
          <p className="text-sm text-gray-500 mt-4">
            Asegurate de verificar la firma antes de procesar cualquier evento webhook
            para evitar ataques de suplantacion.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
