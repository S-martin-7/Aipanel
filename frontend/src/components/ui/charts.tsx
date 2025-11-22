"use client";

import * as React from "react";
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart as RechartsBarChart,
  Bar,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  AreaChart as RechartsAreaChart,
  Area,
} from "recharts";
import { cn } from "@/lib/utils";

// Color palette
const COLORS = [
  "#3b82f6", // blue
  "#10b981", // green
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#84cc16", // lime
];

interface ChartContainerProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  description?: string;
}

function ChartContainer({
  children,
  className,
  title,
  description,
}: ChartContainerProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-4", className)}>
      {(title || description) && (
        <div className="mb-4">
          {title && <h3 className="text-lg font-semibold">{title}</h3>}
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      )}
      <div className="h-[300px] w-full">{children}</div>
    </div>
  );
}

// Line Chart
interface LineChartProps {
  data: Record<string, unknown>[];
  xKey: string;
  yKeys: { key: string; name: string; color?: string }[];
  className?: string;
  title?: string;
  description?: string;
  showGrid?: boolean;
  showLegend?: boolean;
}

function LineChart({
  data,
  xKey,
  yKeys,
  className,
  title,
  description,
  showGrid = true,
  showLegend = true,
}: LineChartProps) {
  return (
    <ChartContainer className={className} title={title} description={description}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsLineChart data={data}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" />}
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          {showLegend && <Legend />}
          {yKeys.map((y, index) => (
            <Line
              key={y.key}
              type="monotone"
              dataKey={y.key}
              name={y.name}
              stroke={y.color || COLORS[index % COLORS.length]}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </RechartsLineChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}

// Area Chart
interface AreaChartProps {
  data: Record<string, unknown>[];
  xKey: string;
  yKeys: { key: string; name: string; color?: string }[];
  className?: string;
  title?: string;
  description?: string;
  showGrid?: boolean;
  showLegend?: boolean;
  stacked?: boolean;
}

function AreaChart({
  data,
  xKey,
  yKeys,
  className,
  title,
  description,
  showGrid = true,
  showLegend = true,
  stacked = false,
}: AreaChartProps) {
  return (
    <ChartContainer className={className} title={title} description={description}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsAreaChart data={data}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" />}
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          {showLegend && <Legend />}
          {yKeys.map((y, index) => (
            <Area
              key={y.key}
              type="monotone"
              dataKey={y.key}
              name={y.name}
              stroke={y.color || COLORS[index % COLORS.length]}
              fill={y.color || COLORS[index % COLORS.length]}
              fillOpacity={0.3}
              stackId={stacked ? "1" : undefined}
            />
          ))}
        </RechartsAreaChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}

// Bar Chart
interface BarChartProps {
  data: Record<string, unknown>[];
  xKey: string;
  yKeys: { key: string; name: string; color?: string }[];
  className?: string;
  title?: string;
  description?: string;
  showGrid?: boolean;
  showLegend?: boolean;
  stacked?: boolean;
  horizontal?: boolean;
}

function BarChart({
  data,
  xKey,
  yKeys,
  className,
  title,
  description,
  showGrid = true,
  showLegend = true,
  stacked = false,
}: BarChartProps) {
  return (
    <ChartContainer className={className} title={title} description={description}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsBarChart data={data}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" />}
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          {showLegend && <Legend />}
          {yKeys.map((y, index) => (
            <Bar
              key={y.key}
              dataKey={y.key}
              name={y.name}
              fill={y.color || COLORS[index % COLORS.length]}
              stackId={stacked ? "1" : undefined}
            />
          ))}
        </RechartsBarChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}

// Pie Chart
interface PieChartDataItem {
  name: string;
  value: number;
  color?: string;
}

interface PieChartProps {
  data: PieChartDataItem[];
  className?: string;
  title?: string;
  description?: string;
  showLegend?: boolean;
  innerRadius?: number;
  outerRadius?: number;
}

function PieChart({
  data,
  className,
  title,
  description,
  showLegend = true,
  innerRadius = 0,
  outerRadius = 80,
}: PieChartProps) {
  return (
    <ChartContainer className={className} title={title} description={description}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsPieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            fill="#8884d8"
            dataKey="value"
            label={({ name, percent }) =>
              `${name}: ${(percent * 100).toFixed(0)}%`
            }
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color || COLORS[index % COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip />
          {showLegend && <Legend />}
        </RechartsPieChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}

// Stat Card
interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  icon?: React.ReactNode;
  className?: string;
}

function StatCard({
  title,
  value,
  description,
  trend,
  icon,
  className,
}: StatCardProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-6", className)}>
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        {icon && <div className="text-muted-foreground">{icon}</div>}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <p className="text-2xl font-bold">{value}</p>
        {trend && (
          <span
            className={cn(
              "text-sm font-medium",
              trend.isPositive ? "text-green-600" : "text-red-600"
            )}
          >
            {trend.isPositive ? "+" : ""}
            {trend.value}%
          </span>
        )}
      </div>
      {description && (
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      )}
    </div>
  );
}

// Stats Grid
interface StatsGridProps {
  children: React.ReactNode;
  columns?: 2 | 3 | 4;
  className?: string;
}

function StatsGrid({ children, columns = 4, className }: StatsGridProps) {
  const gridCols = {
    2: "grid-cols-1 md:grid-cols-2",
    3: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 md:grid-cols-2 lg:grid-cols-4",
  };

  return (
    <div className={cn("grid gap-4", gridCols[columns], className)}>
      {children}
    </div>
  );
}

export {
  ChartContainer,
  LineChart,
  AreaChart,
  BarChart,
  PieChart,
  StatCard,
  StatsGrid,
  COLORS,
};
export type {
  ChartContainerProps,
  LineChartProps,
  AreaChartProps,
  BarChartProps,
  PieChartProps,
  PieChartDataItem,
  StatCardProps,
  StatsGridProps,
};
