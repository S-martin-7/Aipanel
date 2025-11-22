"use client";

import React from "react";
import { Plus, Search, MoreVertical, Eye, Edit, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataTable, Column } from "@/components/ui/table";
import { StatusBadge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";

interface Tenant {
  id: string;
  name: string;
  email: string;
  plan: string;
  status: "active" | "inactive" | "trial" | "suspended";
  agents: number;
  users: number;
  mrr: number;
  createdAt: string;
}

// Mock data
const mockTenants: Tenant[] = [
  { id: "1", name: "TechCorp SpA", email: "admin@techcorp.cl", plan: "Pro", status: "active", agents: 5, users: 12, mrr: 59990, createdAt: "2024-01-15" },
  { id: "2", name: "Marketing Pro", email: "info@marketingpro.cl", plan: "Enterprise", status: "active", agents: 15, users: 45, mrr: 149990, createdAt: "2024-02-20" },
  { id: "3", name: "Consultora ABC", email: "contacto@abc.cl", plan: "Básico", status: "active", agents: 2, users: 3, mrr: 19990, createdAt: "2024-03-10" },
  { id: "4", name: "Retail Solutions", email: "admin@retail.cl", plan: "Pro", status: "trial", agents: 3, users: 8, mrr: 0, createdAt: "2024-06-01" },
  { id: "5", name: "DataTech", email: "hello@datatech.cl", plan: "Pro", status: "suspended", agents: 4, users: 10, mrr: 59990, createdAt: "2024-04-05" },
];

function formatCLP(value: number): string {
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function TenantsPage() {
  const [search, setSearch] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState<string>("all");
  const [planFilter, setPlanFilter] = React.useState<string>("all");
  const [createDialogOpen, setCreateDialogOpen] = React.useState(false);
  const [currentPage, setCurrentPage] = React.useState(1);

  // Filter tenants
  const filteredTenants = mockTenants.filter((tenant) => {
    const matchesSearch =
      tenant.name.toLowerCase().includes(search.toLowerCase()) ||
      tenant.email.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || tenant.status === statusFilter;
    const matchesPlan = planFilter === "all" || tenant.plan === planFilter;
    return matchesSearch && matchesStatus && matchesPlan;
  });

  const columns: Column<Tenant>[] = [
    {
      key: "name",
      header: "Tenant",
      sortable: true,
      render: (tenant) => (
        <div>
          <p className="font-medium">{tenant.name}</p>
          <p className="text-sm text-muted-foreground">{tenant.email}</p>
        </div>
      ),
    },
    {
      key: "plan",
      header: "Plan",
      sortable: true,
    },
    {
      key: "status",
      header: "Estado",
      render: (tenant) => <StatusBadge status={tenant.status} />,
    },
    {
      key: "agents",
      header: "Agentes",
      sortable: true,
    },
    {
      key: "users",
      header: "Usuarios",
      sortable: true,
    },
    {
      key: "mrr",
      header: "MRR",
      sortable: true,
      render: (tenant) => formatCLP(tenant.mrr),
    },
    {
      key: "actions",
      header: "",
      render: (tenant) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Eye className="h-4 w-4 mr-2" /> Ver detalles
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Edit className="h-4 w-4 mr-2" /> Editar
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-red-600">
              <Trash2 className="h-4 w-4 mr-2" /> Eliminar
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Tenants</h2>
          <p className="text-muted-foreground">
            Gestiona los clientes de la plataforma
          </p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" /> Nuevo Tenant
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por nombre o email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="active">Activo</SelectItem>
            <SelectItem value="trial">Trial</SelectItem>
            <SelectItem value="suspended">Suspendido</SelectItem>
          </SelectContent>
        </Select>
        <Select value={planFilter} onValueChange={setPlanFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Plan" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="Básico">Básico</SelectItem>
            <SelectItem value="Pro">Pro</SelectItem>
            <SelectItem value="Enterprise">Enterprise</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <DataTable
        data={filteredTenants}
        columns={columns}
        pagination={{
          currentPage,
          totalPages: Math.ceil(filteredTenants.length / 10),
          totalItems: filteredTenants.length,
          itemsPerPage: 10,
          onPageChange: setCurrentPage,
        }}
        emptyMessage="No se encontraron tenants"
      />

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Crear Nuevo Tenant</DialogTitle>
            <DialogDescription>
              Agrega un nuevo cliente a la plataforma
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Nombre de la empresa</label>
              <Input placeholder="Ej: Mi Empresa SpA" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Email de contacto</label>
              <Input type="email" placeholder="admin@empresa.cl" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Plan</label>
              <Select>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar plan" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="basico">Básico - $19.990/mes</SelectItem>
                  <SelectItem value="pro">Pro - $59.990/mes</SelectItem>
                  <SelectItem value="enterprise">Enterprise - $149.990/mes</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={() => setCreateDialogOpen(false)}>
              Crear Tenant
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
