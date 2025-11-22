"use client";

import React from "react";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  StatCard,
  StatsGrid,
  LineChart,
  BarChart,
  AreaChart,
  PieChart,
} from "@/components/ui/charts";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";

// Mock data
const revenueTimeline = [
  { date: "01 Jun", mrr: 4200000, arr: 50400000, churn: 2.1 },
  { date: "08 Jun", mrr: 4350000, arr: 52200000, churn: 1.8 },
  { date: "15 Jun", mrr: 4500000, arr: 54000000, churn: 1.5 },
  { date: "22 Jun", mrr: 4650000, arr: 55800000, churn: 1.9 },
  { date: "29 Jun", mrr: 4890000, arr: 58680000, churn: 1.7 },
];

const tokenUsage = [
  { date: "01 Jun", input: 12500000, output: 8500000 },
  { date: "08 Jun", input: 14200000, output: 9800000 },
  { date: "15 Jun", input: 15800000, output: 10500000 },
  { date: "22 Jun", input: 17500000, output: 11200000 },
  { date: "29 Jun", input: 19200000, output: 12800000 },
];

const tenantGrowth = [
  { month: "Ene", nuevos: 15, cancelados: 3, neto: 12 },
  { month: "Feb", nuevos: 18, cancelados: 2, neto: 16 },
  { month: "Mar", nuevos: 22, cancelados: 4, neto: 18 },
  { month: "Abr", nuevos: 25, cancelados: 3, neto: 22 },
  { month: "May", nuevos: 28, cancelados: 5, neto: 23 },
  { month: "Jun", nuevos: 32, cancelados: 4, neto: 28 },
];

const modelUsageDistribution = [
  { name: "GPT-4o", value: 35, cost: 1250000 },
  { name: "GPT-4o-mini", value: 40, cost: 320000 },
  { name: "Claude Sonnet 4", value: 15, cost: 580000 },
  { name: "Claude Haiku", value: 10, cost: 95000 },
];

function formatCLP(value: number): string {
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatNumber(value: number): string {
  if (value >= 1000000) {
    return (value / 1000000).toFixed(1) + "M";
  }
  if (value >= 1000) {
    return (value / 1000).toFixed(1) + "K";
  }
  return value.toString();
}

export default function AnalyticsPage() {
  const [period, setPeriod] = React.useState("30d");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Analytics</h2>
          <p className="text-muted-foreground">
            Métricas globales de la plataforma
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Período" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Últimos 7 días</SelectItem>
              <SelectItem value="30d">Últimos 30 días</SelectItem>
              <SelectItem value="90d">Últimos 90 días</SelectItem>
              <SelectItem value="1y">Último año</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" /> Exportar
          </Button>
        </div>
      </div>

      {/* KPIs */}
      <StatsGrid columns={4}>
        <StatCard
          title="MRR"
          value={formatCLP(4890000)}
          trend={{ value: 12.5, isPositive: true }}
          description="Ingresos recurrentes mensuales"
        />
        <StatCard
          title="ARR"
          value={formatCLP(58680000)}
          trend={{ value: 12.5, isPositive: true }}
          description="Proyección anual"
        />
        <StatCard
          title="Churn Rate"
          value="1.7%"
          trend={{ value: 0.4, isPositive: true }}
          description="Tasa de cancelación"
        />
        <StatCard
          title="ARPT"
          value={formatCLP(31346)}
          trend={{ value: 5.2, isPositive: true }}
          description="Ingreso promedio por tenant"
        />
      </StatsGrid>

      {/* Tabs */}
      <Tabs defaultValue="revenue">
        <TabsList>
          <TabsTrigger value="revenue">Ingresos</TabsTrigger>
          <TabsTrigger value="usage">Uso de Tokens</TabsTrigger>
          <TabsTrigger value="growth">Crecimiento</TabsTrigger>
          <TabsTrigger value="models">Modelos AI</TabsTrigger>
        </TabsList>

        <TabsContent value="revenue" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <LineChart
              title="Evolución de MRR"
              description="Ingresos recurrentes mensuales"
              data={revenueTimeline}
              xKey="date"
              yKeys={[
                { key: "mrr", name: "MRR", color: "#3b82f6" },
              ]}
            />
            <AreaChart
              title="Proyección ARR"
              description="Ingresos anualizados"
              data={revenueTimeline}
              xKey="date"
              yKeys={[
                { key: "arr", name: "ARR", color: "#10b981" },
              ]}
            />
          </div>

          {/* Revenue breakdown */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Desglose de Ingresos</h3>
            <div className="grid gap-6 md:grid-cols-3">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Planes Base</p>
                <p className="text-2xl font-bold">{formatCLP(4200000)}</p>
                <p className="text-sm text-green-600">85.9% del total</p>
              </div>
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Overages</p>
                <p className="text-2xl font-bold">{formatCLP(580000)}</p>
                <p className="text-sm text-blue-600">11.9% del total</p>
              </div>
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Add-ons</p>
                <p className="text-2xl font-bold">{formatCLP(110000)}</p>
                <p className="text-sm text-purple-600">2.2% del total</p>
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="usage" className="space-y-6">
          <AreaChart
            title="Consumo de Tokens"
            description="Tokens de entrada y salida"
            data={tokenUsage}
            xKey="date"
            yKeys={[
              { key: "input", name: "Input Tokens", color: "#3b82f6" },
              { key: "output", name: "Output Tokens", color: "#10b981" },
            ]}
            stacked
          />

          <StatsGrid columns={4}>
            <StatCard
              title="Total Tokens"
              value={formatNumber(89500000)}
              description="Este mes"
            />
            <StatCard
              title="Costo Promedio"
              value="$0.0012"
              description="Por 1K tokens"
            />
            <StatCard
              title="Tenants Activos"
              value="142"
              description="Con uso este mes"
            />
            <StatCard
              title="Pico de Uso"
              value={formatNumber(3200000)}
              description="Tokens en un día"
            />
          </StatsGrid>
        </TabsContent>

        <TabsContent value="growth" className="space-y-6">
          <BarChart
            title="Crecimiento de Tenants"
            description="Nuevos vs cancelados por mes"
            data={tenantGrowth}
            xKey="month"
            yKeys={[
              { key: "nuevos", name: "Nuevos", color: "#10b981" },
              { key: "cancelados", name: "Cancelados", color: "#ef4444" },
            ]}
          />

          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Métricas de Retención</h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Net Revenue Retention</span>
                  <span className="font-bold text-green-600">108%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Gross Revenue Retention</span>
                  <span className="font-bold">96%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Tasa de Upgrades</span>
                  <span className="font-bold text-blue-600">12%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Tasa de Downgrades</span>
                  <span className="font-bold text-yellow-600">3%</span>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Lifetime Value</h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">LTV Promedio</span>
                  <span className="font-bold">{formatCLP(752280)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">CAC</span>
                  <span className="font-bold">{formatCLP(125000)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">LTV:CAC Ratio</span>
                  <span className="font-bold text-green-600">6.0x</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Tiempo de vida promedio</span>
                  <span className="font-bold">24 meses</span>
                </div>
              </div>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="models" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <PieChart
              title="Distribución por Modelo"
              description="Porcentaje de uso por modelo AI"
              data={modelUsageDistribution}
            />

            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Costo por Modelo</h3>
              <div className="space-y-4">
                {modelUsageDistribution.map((model) => (
                  <div key={model.name} className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{model.name}</p>
                      <p className="text-sm text-muted-foreground">{model.value}% del uso</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold">{formatCLP(model.cost)}</p>
                      <p className="text-sm text-muted-foreground">este mes</p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <StatsGrid columns={4}>
            <StatCard
              title="Costo Total AI"
              value={formatCLP(2245000)}
              description="Este mes"
            />
            <StatCard
              title="Margen"
              value="54%"
              trend={{ value: 3.2, isPositive: true }}
              description="Sobre costo AI"
            />
            <StatCard
              title="Requests"
              value={formatNumber(156789)}
              description="Llamadas a API"
            />
            <StatCard
              title="Latencia Promedio"
              value="1.2s"
              description="Tiempo de respuesta"
            />
          </StatsGrid>
        </TabsContent>
      </Tabs>
    </div>
  );
}
