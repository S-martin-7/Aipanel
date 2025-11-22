"use client";

import React from "react";
import { Save, Eye, EyeOff, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";

export default function AdminSettingsPage() {
  const [showOpenAIKey, setShowOpenAIKey] = React.useState(false);
  const [showAnthropicKey, setShowAnthropicKey] = React.useState(false);
  const [showTransbankKey, setShowTransbankKey] = React.useState(false);
  const [saving, setSaving] = React.useState(false);

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
    }, 1000);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Configuración</h2>
          <p className="text-muted-foreground">
            Ajustes globales de la plataforma
          </p>
        </div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Guardar Cambios
        </Button>
      </div>

      <Tabs defaultValue="general">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="ai">Proveedores AI</TabsTrigger>
          <TabsTrigger value="payments">Pagos</TabsTrigger>
          <TabsTrigger value="email">Email</TabsTrigger>
          <TabsTrigger value="security">Seguridad</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-6">
          <Card className="p-6">
            <h3 className="font-semibold mb-4">Configuración General</h3>
            <div className="space-y-4 max-w-xl">
              <div className="space-y-2">
                <label className="text-sm font-medium">Nombre de la Plataforma</label>
                <Input defaultValue="AIPanel" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">URL del Sistema</label>
                <Input defaultValue="https://app.aipanel.cl" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Email de Soporte</label>
                <Input type="email" defaultValue="soporte@aipanel.cl" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Zona Horaria</label>
                <Select defaultValue="america-santiago">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="america-santiago">America/Santiago (GMT-4)</SelectItem>
                    <SelectItem value="utc">UTC</SelectItem>
                    <SelectItem value="america-lima">America/Lima (GMT-5)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Idioma por Defecto</label>
                <Select defaultValue="es">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="es">Español</SelectItem>
                    <SelectItem value="en">English</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="font-semibold mb-4">Límites del Sistema</h3>
            <div className="grid gap-4 md:grid-cols-2 max-w-xl">
              <div className="space-y-2">
                <label className="text-sm font-medium">Max Agents por Tenant (Trial)</label>
                <Input type="number" defaultValue="1" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Tokens Trial (mensual)</label>
                <Input type="number" defaultValue="10000" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Días de Trial</label>
                <Input type="number" defaultValue="14" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Rate Limit por Minuto</label>
                <Input type="number" defaultValue="20" />
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="ai" className="space-y-6">
          <Alert variant="info">
            <AlertTitle>Claves de API</AlertTitle>
            <AlertDescription>
              Las claves de API se almacenan de forma segura y encriptada. Nunca se muestran completas después de guardarlas.
            </AlertDescription>
          </Alert>

          <Card className="p-6">
            <h3 className="font-semibold mb-4">OpenAI</h3>
            <div className="space-y-4 max-w-xl">
              <div className="space-y-2">
                <label className="text-sm font-medium">API Key</label>
                <div className="relative">
                  <Input
                    type={showOpenAIKey ? "text" : "password"}
                    defaultValue="sk-proj-xxxxxxxxxxxxxxxxxxxx"
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2"
                    onClick={() => setShowOpenAIKey(!showOpenAIKey)}
                  >
                    {showOpenAIKey ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    )}
                  </button>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Organization ID (opcional)</label>
                <Input defaultValue="" placeholder="org-xxxxxxxx" />
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="font-semibold mb-4">Anthropic</h3>
            <div className="space-y-4 max-w-xl">
              <div className="space-y-2">
                <label className="text-sm font-medium">API Key</label>
                <div className="relative">
                  <Input
                    type={showAnthropicKey ? "text" : "password"}
                    defaultValue="sk-ant-xxxxxxxxxxxxxxxxxxxx"
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2"
                    onClick={() => setShowAnthropicKey(!showAnthropicKey)}
                  >
                    {showAnthropicKey ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="payments" className="space-y-6">
          <Card className="p-6">
            <h3 className="font-semibold mb-4">Transbank WebPay</h3>
            <div className="space-y-4 max-w-xl">
              <div className="space-y-2">
                <label className="text-sm font-medium">Ambiente</label>
                <Select defaultValue="integration">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="integration">Integración (Testing)</SelectItem>
                    <SelectItem value="production">Producción</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Código de Comercio</label>
                <Input defaultValue="597055555532" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">API Key</label>
                <div className="relative">
                  <Input
                    type={showTransbankKey ? "text" : "password"}
                    defaultValue="579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 -translate-y-1/2"
                    onClick={() => setShowTransbankKey(!showTransbankKey)}
                  >
                    {showTransbankKey ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="font-semibold mb-4">Facturación Electrónica (SII)</h3>
            <div className="space-y-4 max-w-xl">
              <div className="space-y-2">
                <label className="text-sm font-medium">RUT Empresa</label>
                <Input defaultValue="76.xxx.xxx-x" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Razón Social</label>
                <Input defaultValue="AIPanel SpA" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Certificado Digital</label>
                <Input type="file" accept=".pfx,.p12" />
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="email" className="space-y-6">
          <Card className="p-6">
            <h3 className="font-semibold mb-4">Configuración SMTP</h3>
            <div className="space-y-4 max-w-xl">
              <div className="space-y-2">
                <label className="text-sm font-medium">Servidor SMTP</label>
                <Input defaultValue="smtp.sendgrid.net" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Puerto</label>
                  <Input type="number" defaultValue="587" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Seguridad</label>
                  <Select defaultValue="tls">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Ninguna</SelectItem>
                      <SelectItem value="tls">TLS</SelectItem>
                      <SelectItem value="ssl">SSL</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Usuario</label>
                <Input defaultValue="apikey" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Contraseña / API Key</label>
                <Input type="password" defaultValue="SG.xxxxxxxxxxxx" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Email Remitente</label>
                <Input type="email" defaultValue="no-reply@aipanel.cl" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Nombre Remitente</label>
                <Input defaultValue="AIPanel" />
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="space-y-6">
          <Card className="p-6">
            <h3 className="font-semibold mb-4">Configuración JWT</h3>
            <div className="space-y-4 max-w-xl">
              <div className="space-y-2">
                <label className="text-sm font-medium">Tiempo de Expiración (minutos)</label>
                <Input type="number" defaultValue="15" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Tiempo Refresh Token (días)</label>
                <Input type="number" defaultValue="7" />
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="font-semibold mb-4">Rate Limiting</h3>
            <div className="space-y-4 max-w-xl">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Plan Básico (req/min)</label>
                  <Input type="number" defaultValue="5" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Plan Pro (req/min)</label>
                  <Input type="number" defaultValue="20" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Plan Enterprise (req/min)</label>
                  <Input type="number" defaultValue="100" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Admin (req/min)</label>
                  <Input type="number" defaultValue="200" />
                </div>
              </div>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
