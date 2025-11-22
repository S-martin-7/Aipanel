"use client";

import { useState, useEffect } from "react";
import { Key, Plus, Trash2, RefreshCw, CheckCircle, XCircle, Eye, EyeOff, ExternalLink } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

// Types
interface APIKey {
  id: string;
  provider_type: string;
  provider_name: string;
  organization_id?: string;
  base_url?: string;
  is_active: boolean;
  is_valid: boolean;
  api_key_masked: string;
  last_validated_at?: string;
  last_error?: string;
  created_at: string;
  updated_at?: string;
}

interface Provider {
  provider_type: string;
  provider_name: string;
  description: string;
  config_help: string;
  is_configured: boolean;
}

export default function APIKeysPage() {
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [validating, setValidating] = useState<string | null>(null);
  const [showKey, setShowKey] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    provider_type: "OPENAI",
    provider_name: "OpenAI",
    api_key: "",
    organization_id: "",
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [keysRes, providersRes] = await Promise.all([
        api.get("/settings/api-keys"),
        api.get("/settings/providers"),
      ]);
      setKeys(keysRes.items || []);
      setProviders(providersRes.providers || []);
    } catch (error) {
      console.error("Error loading API keys:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/settings/api-keys", formData);
      setShowForm(false);
      setFormData({
        provider_type: "OPENAI",
        provider_name: "OpenAI",
        api_key: "",
        organization_id: "",
      });
      loadData();
    } catch (error) {
      console.error("Error saving API key:", error);
      alert("Error al guardar la API key");
    }
  };

  const handleDelete = async (keyId: string) => {
    if (!confirm("Estas seguro de eliminar esta API key?")) return;
    try {
      await api.delete(`/settings/api-keys/${keyId}`);
      loadData();
    } catch (error) {
      console.error("Error deleting API key:", error);
    }
  };

  const handleValidate = async (keyId: string) => {
    try {
      setValidating(keyId);
      await api.post(`/settings/api-keys/${keyId}/validate`);
      loadData();
    } catch (error) {
      console.error("Error validating API key:", error);
    } finally {
      setValidating(null);
    }
  };

  const toggleActive = async (key: APIKey) => {
    try {
      await api.patch(`/settings/api-keys/${key.id}`, {
        is_active: !key.is_active,
      });
      loadData();
    } catch (error) {
      console.error("Error toggling API key:", error);
    }
  };

  const handleProviderChange = (providerType: string) => {
    const provider = providers.find((p) => p.provider_type === providerType);
    setFormData({
      ...formData,
      provider_type: providerType,
      provider_name: provider?.provider_name || providerType,
    });
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
          <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
          <p className="text-gray-500 mt-1">
            Configura tus claves de API para los proveedores de IA
          </p>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Agregar API Key
        </Button>
      </div>

      {/* Provider Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {providers.map((provider) => {
          const configured = keys.some(
            (k) => k.provider_type === provider.provider_type && k.is_active
          );
          return (
            <Card
              key={provider.provider_type}
              className={configured ? "border-green-200 bg-green-50" : ""}
            >
              <CardContent className="pt-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      {provider.provider_name}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">
                      {provider.description}
                    </p>
                  </div>
                  {configured ? (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  ) : (
                    <XCircle className="w-5 h-5 text-gray-300" />
                  )}
                </div>
                <a
                  href={provider.config_help.replace("Get your API key from ", "")}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary-600 hover:underline mt-2 inline-flex items-center gap-1"
                >
                  Obtener API Key
                  <ExternalLink className="w-3 h-3" />
                </a>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Add Form */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>Nueva API Key</CardTitle>
            <CardDescription>
              Agrega una nueva clave de API para un proveedor de IA
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Proveedor
                </label>
                <select
                  value={formData.provider_type}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {providers.map((p) => (
                    <option key={p.provider_type} value={p.provider_type}>
                      {p.provider_name}
                    </option>
                  ))}
                </select>
              </div>

              <Input
                label="API Key"
                type="password"
                value={formData.api_key}
                onChange={(e) =>
                  setFormData({ ...formData, api_key: e.target.value })
                }
                placeholder="sk-..."
                required
              />

              {formData.provider_type === "OPENAI" && (
                <Input
                  label="Organization ID (opcional)"
                  value={formData.organization_id}
                  onChange={(e) =>
                    setFormData({ ...formData, organization_id: e.target.value })
                  }
                  placeholder="org-..."
                />
              )}

              <div className="flex gap-3">
                <Button type="submit">Guardar</Button>
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

      {/* Existing Keys */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="w-5 h-5" />
            Claves Configuradas
          </CardTitle>
          <CardDescription>
            Gestiona tus claves de API existentes
          </CardDescription>
        </CardHeader>
        <CardContent>
          {keys.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Key className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>No tienes API keys configuradas</p>
              <p className="text-sm mt-1">
                Agrega una clave para empezar a usar los agentes de IA
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {keys.map((key) => (
                <div
                  key={key.id}
                  className={`p-4 border rounded-lg ${
                    key.is_active
                      ? key.is_valid
                        ? "border-green-200 bg-green-50"
                        : "border-yellow-200 bg-yellow-50"
                      : "border-gray-200 bg-gray-50"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-gray-900">
                          {key.provider_name}
                        </h4>
                        {key.is_active ? (
                          key.is_valid ? (
                            <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded">
                              Activa
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-700 rounded">
                              Invalida
                            </span>
                          )
                        ) : (
                          <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                            Desactivada
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2 mt-2">
                        <code className="text-sm font-mono text-gray-600 bg-gray-100 px-2 py-1 rounded">
                          {showKey === key.id
                            ? key.api_key_masked
                            : key.api_key_masked}
                        </code>
                        <button
                          onClick={() =>
                            setShowKey(showKey === key.id ? null : key.id)
                          }
                          className="text-gray-400 hover:text-gray-600"
                        >
                          {showKey === key.id ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                      </div>

                      {key.organization_id && (
                        <p className="text-sm text-gray-500 mt-1">
                          Org: {key.organization_id}
                        </p>
                      )}

                      {key.last_error && (
                        <p className="text-sm text-red-600 mt-2">
                          Error: {key.last_error}
                        </p>
                      )}

                      {key.last_validated_at && (
                        <p className="text-xs text-gray-400 mt-2">
                          Ultima validacion:{" "}
                          {new Date(key.last_validated_at).toLocaleString()}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleValidate(key.id)}
                        disabled={validating === key.id}
                      >
                        <RefreshCw
                          className={`w-4 h-4 ${
                            validating === key.id ? "animate-spin" : ""
                          }`}
                        />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleActive(key)}
                      >
                        {key.is_active ? "Desactivar" : "Activar"}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(key.id)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Help Section */}
      <Card>
        <CardHeader>
          <CardTitle>Como configurar API Keys</CardTitle>
        </CardHeader>
        <CardContent className="prose prose-sm max-w-none">
          <ol className="space-y-2 text-gray-600">
            <li>
              <strong>OpenAI:</strong> Ve a{" "}
              <a
                href="https://platform.openai.com/api-keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:underline"
              >
                platform.openai.com/api-keys
              </a>{" "}
              y crea una nueva API key
            </li>
            <li>
              <strong>Anthropic:</strong> Ve a{" "}
              <a
                href="https://console.anthropic.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:underline"
              >
                console.anthropic.com
              </a>{" "}
              y genera una API key
            </li>
            <li>
              <strong>Google AI:</strong> Ve a{" "}
              <a
                href="https://aistudio.google.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:underline"
              >
                aistudio.google.com
              </a>{" "}
              para obtener tu API key
            </li>
          </ol>
          <p className="mt-4 text-sm text-gray-500">
            Las API keys se almacenan de forma encriptada y solo tu puedes
            acceder a ellas.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
