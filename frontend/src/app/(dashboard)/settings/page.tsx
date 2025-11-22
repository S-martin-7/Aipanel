"use client";

import Link from "next/link";
import { Settings, User, Key, Bell, ChevronRight, Cpu } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/lib/store";

export default function SettingsPage() {
  const { user } = useAuthStore();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Configuracion</h1>
        <p className="text-gray-500 mt-1">Gestiona tu cuenta y preferencias</p>
      </div>

      {/* API Keys Link */}
      <Link href="/settings/api-keys">
        <Card className="hover:border-primary-300 hover:shadow-sm transition-all cursor-pointer">
          <CardContent className="flex items-center justify-between py-4">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                <Cpu className="w-5 h-5 text-primary-600" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900">API Keys de IA</h3>
                <p className="text-sm text-gray-500">
                  Configura las claves de API para OpenAI, Anthropic y otros proveedores
                </p>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </CardContent>
        </Card>
      </Link>

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="w-5 h-5" />
            Perfil
          </CardTitle>
          <CardDescription>Información de tu cuenta</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Nombre"
              defaultValue={user?.name || ""}
              placeholder="Tu nombre"
            />
            <Input
              label="Correo electrónico"
              type="email"
              defaultValue={user?.email || ""}
              disabled
            />
          </div>
          <Button>Guardar Cambios</Button>
        </CardContent>
      </Card>

      {/* Security */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="w-5 h-5" />
            Seguridad
          </CardTitle>
          <CardDescription>Contraseña y autenticación</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Contraseña actual"
              type="password"
              placeholder="••••••••"
            />
            <div></div>
            <Input
              label="Nueva contraseña"
              type="password"
              placeholder="••••••••"
            />
            <Input
              label="Confirmar contraseña"
              type="password"
              placeholder="••••••••"
            />
          </div>
          <Button>Cambiar Contraseña</Button>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5" />
            Notificaciones
          </CardTitle>
          <CardDescription>Preferencias de notificación</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <label className="flex items-center gap-3">
              <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
              <div>
                <p className="text-sm font-medium text-gray-900">Alertas de uso</p>
                <p className="text-sm text-gray-500">Recibe alertas cuando tu uso se acerque al límite</p>
              </div>
            </label>
            <label className="flex items-center gap-3">
              <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
              <div>
                <p className="text-sm font-medium text-gray-900">Resumen semanal</p>
                <p className="text-sm text-gray-500">Recibe un resumen de actividad cada semana</p>
              </div>
            </label>
            <label className="flex items-center gap-3">
              <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
              <div>
                <p className="text-sm font-medium text-gray-900">Novedades del producto</p>
                <p className="text-sm text-gray-500">Entérate de nuevas funciones y actualizaciones</p>
              </div>
            </label>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-red-200">
        <CardHeader>
          <CardTitle className="text-red-600">Zona de Peligro</CardTitle>
          <CardDescription>Acciones irreversibles</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="danger">Eliminar Cuenta</Button>
        </CardContent>
      </Card>
    </div>
  );
}
