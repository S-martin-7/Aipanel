"use client";

import { useQuery } from "@tanstack/react-query";
import { BarChart3, TrendingUp, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usageApi } from "@/lib/api";
import { formatNumber } from "@/lib/utils";

export default function UsagePage() {
  const { data: quota } = useQuery({
    queryKey: ["usage-quota"],
    queryFn: usageApi.getQuota,
  });

  const { data: summary } = useQuery({
    queryKey: ["usage-summary"],
    queryFn: () => usageApi.getSummary("monthly"),
  });

  const percentage = quota ? (quota.tokens_used / quota.tokens_limit) * 100 : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Uso</h1>
        <p className="text-gray-500 mt-1">Monitorea tu consumo de tokens</p>
      </div>

      {/* Quota Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary-600" />
            Cuota del Mes
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex justify-between items-end">
              <div>
                <p className="text-3xl font-bold text-gray-900">
                  {formatNumber(quota?.tokens_used || 0)}
                </p>
                <p className="text-sm text-gray-500">
                  de {formatNumber(quota?.tokens_limit || 0)} tokens
                </p>
              </div>
              <p className={`text-lg font-semibold ${
                percentage > 90 ? "text-red-600" : percentage > 70 ? "text-yellow-600" : "text-green-600"
              }`}>
                {percentage.toFixed(1)}%
              </p>
            </div>
            <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  percentage > 90 ? "bg-red-500" : percentage > 70 ? "bg-yellow-500" : "bg-green-500"
                }`}
                style={{ width: `${Math.min(percentage, 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-sm text-gray-500">
              <span>Reinicio: {quota?.reset_date || "--"}</span>
              <span>Plan: {quota?.plan || "Free"}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center">
                <BarChart3 className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Solicitudes</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatNumber(summary?.total_requests || 0)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-green-50 rounded-xl flex items-center justify-center">
                <Zap className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Tokens Totales</p>
                <p className="text-2xl font-bold text-gray-900">
                  {formatNumber(summary?.total_tokens || 0)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Costo Estimado</p>
                <p className="text-2xl font-bold text-gray-900">
                  ${(summary?.estimated_cost_usd || 0).toFixed(2)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Chart Placeholder */}
      <Card>
        <CardHeader>
          <CardTitle>Uso Diario</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center text-gray-400">
            Gráfico de uso (próximamente)
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
