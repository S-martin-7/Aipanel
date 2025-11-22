"use client";

import { useQuery } from "@tanstack/react-query";
import { CreditCard, Check, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { paymentsApi } from "@/lib/api";
import { formatCurrency, formatDate, formatNumber } from "@/lib/utils";

export default function BillingPage() {
  const { data: subscription } = useQuery({
    queryKey: ["subscription"],
    queryFn: paymentsApi.getSubscription,
  });

  const { data: plans } = useQuery({
    queryKey: ["plans"],
    queryFn: paymentsApi.getPlans,
  });

  const { data: history } = useQuery({
    queryKey: ["payment-history"],
    queryFn: paymentsApi.getHistory,
  });

  const currentPlan = subscription?.plan || "free";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Facturación</h1>
        <p className="text-gray-500 mt-1">Gestiona tu suscripción y pagos</p>
      </div>

      {/* Current Plan */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary-600" />
            Plan Actual
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {subscription?.plan_details?.name || "Gratis"}
              </p>
              <p className="text-sm text-gray-500 mt-1">
                {subscription?.plan_details?.price_clp
                  ? formatCurrency(subscription.plan_details.price_clp) + "/mes"
                  : "Sin costo"}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-500">Período actual</p>
              <p className="text-sm font-medium">
                {subscription?.current_period_start
                  ? `${formatDate(subscription.current_period_start)} - ${formatDate(subscription.current_period_end)}`
                  : "--"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Plans */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Planes Disponibles</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {plans?.map((plan) => (
            <Card
              key={plan.plan}
              className={currentPlan === plan.plan ? "ring-2 ring-primary-500" : ""}
            >
              <CardContent className="p-6">
                <h3 className="font-semibold text-gray-900">{plan.name}</h3>
                <p className="text-2xl font-bold text-gray-900 mt-2">
                  {plan.price_clp === 0 ? "Gratis" : formatCurrency(plan.price_clp)}
                </p>
                {plan.price_clp > 0 && (
                  <p className="text-sm text-gray-500">/mes</p>
                )}

                <ul className="mt-4 space-y-2">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-center gap-2 text-sm text-gray-600">
                      <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                      {feature}
                    </li>
                  ))}
                </ul>

                <Button
                  className="w-full mt-4"
                  variant={currentPlan === plan.plan ? "secondary" : "primary"}
                  disabled={currentPlan === plan.plan}
                >
                  {currentPlan === plan.plan ? "Plan Actual" : "Seleccionar"}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Payment History */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="w-5 h-5" />
            Historial de Pagos
          </CardTitle>
        </CardHeader>
        <CardContent>
          {history?.payments?.length === 0 ? (
            <p className="text-center text-gray-500 py-8">
              No hay pagos registrados
            </p>
          ) : (
            <div className="divide-y divide-gray-100">
              {history?.payments?.map((payment: any) => (
                <div key={payment.id} className="flex items-center justify-between py-3">
                  <div>
                    <p className="font-medium text-gray-900">
                      {formatCurrency(payment.amount)}
                    </p>
                    <p className="text-sm text-gray-500">
                      {formatDate(payment.created_at)}
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    payment.status === "completed"
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-600"
                  }`}>
                    {payment.status === "completed" ? "Completado" : payment.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
