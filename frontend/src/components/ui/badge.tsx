import * as React from "react";
import { cn } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "bg-primary text-primary-foreground hover:bg-primary/80",
    secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
    destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/80",
    outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
    success: "bg-green-500 text-white hover:bg-green-600",
    warning: "bg-yellow-500 text-white hover:bg-yellow-600",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

// Status Badge with predefined statuses
interface StatusBadgeProps {
  status: "active" | "inactive" | "pending" | "error" | "trial" | "suspended";
  className?: string;
}

function StatusBadge({ status, className }: StatusBadgeProps) {
  const statusConfig = {
    active: { variant: "success" as const, label: "Activo" },
    inactive: { variant: "secondary" as const, label: "Inactivo" },
    pending: { variant: "warning" as const, label: "Pendiente" },
    error: { variant: "destructive" as const, label: "Error" },
    trial: { variant: "outline" as const, label: "Trial" },
    suspended: { variant: "destructive" as const, label: "Suspendido" },
  };

  const config = statusConfig[status];

  return (
    <Badge variant={config.variant} className={className}>
      {config.label}
    </Badge>
  );
}

export { Badge, StatusBadge };
export type { BadgeProps, StatusBadgeProps };
