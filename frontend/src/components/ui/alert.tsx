import * as React from "react";
import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle, Info, XCircle, X } from "lucide-react";

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "success" | "warning" | "error" | "info";
  dismissible?: boolean;
  onDismiss?: () => void;
}

function Alert({
  className,
  variant = "default",
  dismissible = false,
  onDismiss,
  children,
  ...props
}: AlertProps) {
  const variants = {
    default: "bg-background border-border",
    success: "bg-green-50 border-green-200 text-green-800 dark:bg-green-950 dark:border-green-800 dark:text-green-200",
    warning: "bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-950 dark:border-yellow-800 dark:text-yellow-200",
    error: "bg-red-50 border-red-200 text-red-800 dark:bg-red-950 dark:border-red-800 dark:text-red-200",
    info: "bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-950 dark:border-blue-800 dark:text-blue-200",
  };

  const icons = {
    default: null,
    success: <CheckCircle className="h-4 w-4" />,
    warning: <AlertCircle className="h-4 w-4" />,
    error: <XCircle className="h-4 w-4" />,
    info: <Info className="h-4 w-4" />,
  };

  return (
    <div
      role="alert"
      className={cn(
        "relative w-full rounded-lg border p-4",
        variants[variant],
        className
      )}
      {...props}
    >
      <div className="flex items-start gap-3">
        {icons[variant] && <span className="mt-0.5">{icons[variant]}</span>}
        <div className="flex-1">{children}</div>
        {dismissible && onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="opacity-70 hover:opacity-100 transition-opacity"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}

function AlertTitle({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h5
      className={cn("mb-1 font-medium leading-none tracking-tight", className)}
      {...props}
    />
  );
}

function AlertDescription({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <div className={cn("text-sm [&_p]:leading-relaxed", className)} {...props} />
  );
}

// Toast notification system
interface ToastProps {
  id: string;
  title?: string;
  description?: string;
  variant?: "default" | "success" | "warning" | "error" | "info";
  duration?: number;
}

interface ToastContextValue {
  toasts: ToastProps[];
  addToast: (toast: Omit<ToastProps, "id">) => void;
  removeToast: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextValue | undefined>(undefined);

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastProps[]>([]);

  const addToast = React.useCallback((toast: Omit<ToastProps, "id">) => {
    const id = Math.random().toString(36).substring(7);
    setToasts((prev) => [...prev, { ...toast, id }]);

    // Auto remove after duration
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, toast.duration || 5000);
  }, []);

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer />
    </ToastContext.Provider>
  );
}

function ToastContainer() {
  const { toasts, removeToast } = useToast();

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <Alert
          key={toast.id}
          variant={toast.variant}
          dismissible
          onDismiss={() => removeToast(toast.id)}
          className="w-80 shadow-lg animate-in slide-in-from-right"
        >
          {toast.title && <AlertTitle>{toast.title}</AlertTitle>}
          {toast.description && (
            <AlertDescription>{toast.description}</AlertDescription>
          )}
        </Alert>
      ))}
    </div>
  );
}

export { Alert, AlertTitle, AlertDescription };
export type { AlertProps, ToastProps };
