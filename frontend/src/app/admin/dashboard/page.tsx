"use client";

import React from "react";
import {
  Users,
  Bot,
  MessageSquare,
  DollarSign,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { StatCard, StatsGrid, LineChart, BarChart, PieChart } from "@/components/ui/charts";
import { Card } from "@/components/ui/card";

// Mock data - en producción vendría de la API
const stats = {
  totalTenants: 156,
  tenantsGrowth: 12.5,
  activeAgents: 423,
  agentsGrowth: 8.2,
  totalConversations: 12543,
  conversationsGrowth: 15.7,
  mrr: 4890000,
  mrrGrowth: 10.3,
};

const revenueData = [
  { month: "Ene", revenue: 3200000, tenants: 120 },
  { month: "Feb", revenue: 3500000, tenants: 128 },
  { month: "Mar", revenue: 3800000, tenants: 135 },
  { month: "Abr", revenue: 4100000, tenants: 142 },
  { month: "May", revenue: 4500000, tenants: 150 },
  { month: "Jun", revenue: 4890000, tenants: 156 },
];

const usageByModel = [
  { name: "GPT-4o", value: 45 },
  { name: "GPT-4o-mini", value: 30 },
  { name: "Claude Sonnet", value: 15 },
  { name: "Claude Haiku", value: 10 },
];

const tenantsByPlan = [
  { plan: "Básico", count: 89, revenue: 890000 },
  { plan: "Pro", count: 52, revenue: 2600000 },
  { plan: "Enterprise", count: 15, revenue: 1400000 },
];

function formatCLP(value: number): string {
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("es-CL").format(value);
}

export default function AdminDashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Dashboard Global</h2>
        <p className="text-muted-foreground">
          Vista general del sistema AIPanel
        </p>
      </div>

      {/* Stats Grid */}
      <StatsGrid columns={4}>
        <StatCard
          title="Total Tenants"
          value={formatNumber(stats.totalTenants)}
          trend={{ value: stats.tenantsGrowth, isPositive: true }}
          icon={<Users className="h-5 w-5" />}
          description="Clientes activos"
        />
        <StatCard
          title="Agentes Activos"
          value={formatNumber(stats.activeAgents)}
          trend={{ value: stats.agentsGrowth, isPositive: true }}
          icon={<Bot className="h-5 w-5" />}
          description="En todos los tenants"
        />
        <StatCard
          title="Conversaciones"
          value={formatNumber(stats.totalConversations)}
          trend={{ value: stats.conversationsGrowth, isPositive: true }}
          icon={<MessageSquare className="h-5 w-5" />}
          description="Este mes"
        />
        <StatCard
          title="MRR"
          value={formatCLP(stats.mrr)}
          trend={{ value: stats.mrrGrowth, isPositive: true }}
          icon={<DollarSign className="h-5 w-5" />}
          description="Ingresos recurrentes"
        />
      </StatsGrid>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        <LineChart
          title="Ingresos Mensuales"
          description="Evolución del MRR en los últimos 6 meses"
          data={revenueData}
          xKey="month"
          yKeys={[{ key: "revenue", name: "Ingresos (CLP)" }]}
        />
        <PieChart
          title="Uso por Modelo"
          description="Distribución de tokens por modelo de AI"
          data={usageByModel}
        />
      </div>

      {/* Tenants by Plan */}
      <div className="grid gap-6 lg:grid-cols-2">
        <BarChart
          title="Tenants por Plan"
          description="Distribución de clientes por tipo de plan"
          data={tenantsByPlan}
          xKey="plan"
          yKeys={[{ key: "count", name: "Cantidad" }]}
        />
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Revenue por Plan</h3>
          <div className="space-y-4">
            {tenantsByPlan.map((plan) => (
              <div key={plan.plan} className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{plan.plan}</p>
                  <p className="text-sm text-muted-foreground">
                    {plan.count} tenants
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-bold">{formatCLP(plan.revenue)}</p>
                  <p className="text-sm text-muted-foreground">
                    {((plan.revenue / stats.mrr) * 100).toFixed(1)}% del MRR
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Actividad Reciente</h3>
        <div className="space-y-4">
          {[
            { action: "Nuevo tenant registrado", tenant: "TechCorp SpA", time: "Hace 5 min", type: "new" },
            { action: "Upgrade a Pro", tenant: "Marketing Pro", time: "Hace 15 min", type: "upgrade" },
            { action: "Pago recibido", tenant: "Consultora ABC", time: "Hace 30 min", type: "payment" },
            { action: "Nuevo agente creado", tenant: "Retail Solutions", time: "Hace 1 hora", type: "agent" },
            { action: "Alerta de uso alto", tenant: "DataTech", time: "Hace 2 horas", type: "alert" },
          ].map((activity, index) => (
            <div key={index} className="flex items-center gap-4 py-2 border-b last:border-0">
              <div className={`h-2 w-2 rounded-full ${
                activity.type === "new" ? "bg-green-500" :
                activity.type === "upgrade" ? "bg-blue-500" :
                activity.type === "payment" ? "bg-emerald-500" :
                activity.type === "alert" ? "bg-yellow-500" :
                "bg-gray-500"
              }`} />
              <div className="flex-1">
                <p className="text-sm font-medium">{activity.action}</p>
                <p className="text-xs text-muted-foreground">{activity.tenant}</p>
              </div>
              <span className="text-xs text-muted-foreground">{activity.time}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
