"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, FileText, MessageSquare, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usageApi, paymentsApi, agentsApi } from "@/lib/api";
import { formatNumber, formatCurrency } from "@/lib/utils";

function StatCard({
  title,
  value,
  description,
  icon: Icon,
}: {
  title: string;
  value: string;
  description?: string;
  icon: React.ElementType;
}) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">{title}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
            {description && (
              <p className="text-xs text-gray-500 mt-1">{description}</p>
            )}
          </div>
          <div className="w-12 h-12 bg-primary-50 rounded-xl flex items-center justify-center">
            <Icon className="w-6 h-6 text-primary-600" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function UsageProgress({ used, limit }: { used: number; limit: number }) {
  const percentage = Math.min((used / limit) * 100, 100);
  const color = percentage > 90 ? "bg-red-500" : percentage > 70 ? "bg-yellow-500" : "bg-primary-500";

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">Tokens utilizados</span>
        <span className="font-medium">
          {formatNumber(used)} / {formatNumber(limit)}
        </span>
      </div>
      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} transition-all`} style={{ width: `${percentage}%` }} />
      </div>
      <p className="text-xs text-gray-500">{percentage.toFixed(1)}% utilizado</p>
    </div>
  );
}

export default function DashboardPage() {
  const { data: quota } = useQuery({
    queryKey: ["usage-quota"],
    queryFn: usageApi.getQuota,
  });

  const { data: subscription } = useQuery({
    queryKey: ["subscription"],
    queryFn: paymentsApi.getSubscription,
  });

  const { data: agents } = useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Resumen de tu cuenta y uso</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Agentes"
          value={agents?.length?.toString() || "0"}
          description={`Límite: ${subscription?.plan_details?.agents_limit || 1}`}
          icon={Bot}
        />
        <StatCard
          title="Conversaciones"
          value="--"
          description="Este mes"
          icon={MessageSquare}
        />
        <StatCard
          title="Documentos"
          value={subscription?.documents_count?.toString() || "0"}
          description={`Límite: ${subscription?.plan_details?.documents_limit || 5}`}
          icon={FileText}
        />
        <StatCard
          title="Plan Actual"
          value={subscription?.plan_details?.name || "Gratis"}
          description={subscription?.plan_details?.price_clp ? formatCurrency(subscription.plan_details.price_clp) + "/mes" : ""}
          icon={Zap}
        />
      </div>

      {/* Usage Card */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Uso de Tokens</CardTitle>
          </CardHeader>
          <CardContent>
            {quota ? (
              <UsageProgress used={quota.tokens_used} limit={quota.tokens_limit} />
            ) : (
              <div className="animate-pulse h-16 bg-gray-100 rounded" />
            )}
            <div className="mt-4 pt-4 border-t border-gray-100">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Reinicio</span>
                <span className="font-medium">{quota?.reset_date || "--"}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Actividad Reciente</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <p className="text-sm text-gray-500 text-center py-8">
                No hay actividad reciente
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
