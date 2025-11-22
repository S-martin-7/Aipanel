/**
 * Internationalization (i18n) system for AIPanel.
 *
 * Supports Spanish (default) and English.
 */

export type Locale = "es" | "en";

export interface Translations {
  [key: string]: string | Translations;
}

// Spanish translations (default)
const es: Translations = {
  common: {
    save: "Guardar",
    cancel: "Cancelar",
    delete: "Eliminar",
    edit: "Editar",
    create: "Crear",
    search: "Buscar",
    filter: "Filtrar",
    loading: "Cargando...",
    error: "Error",
    success: "Éxito",
    confirm: "Confirmar",
    back: "Volver",
    next: "Siguiente",
    previous: "Anterior",
    yes: "Sí",
    no: "No",
    all: "Todos",
    none: "Ninguno",
    select: "Seleccionar",
    upload: "Subir",
    download: "Descargar",
    export: "Exportar",
    import: "Importar",
    copy: "Copiar",
    copied: "Copiado",
    close: "Cerrar",
    open: "Abrir",
    view: "Ver",
    details: "Detalles",
    actions: "Acciones",
    status: "Estado",
    name: "Nombre",
    email: "Email",
    password: "Contraseña",
    description: "Descripción",
    date: "Fecha",
    time: "Hora",
    amount: "Monto",
    total: "Total",
    active: "Activo",
    inactive: "Inactivo",
    pending: "Pendiente",
    completed: "Completado",
    failed: "Fallido",
  },
  auth: {
    login: "Iniciar sesión",
    logout: "Cerrar sesión",
    register: "Registrarse",
    forgotPassword: "¿Olvidaste tu contraseña?",
    resetPassword: "Restablecer contraseña",
    emailPlaceholder: "tu@email.com",
    passwordPlaceholder: "••••••••",
    loginTitle: "Bienvenido de vuelta",
    loginSubtitle: "Ingresa tus credenciales para continuar",
    registerTitle: "Crear cuenta",
    registerSubtitle: "Comienza tu prueba gratuita",
    invalidCredentials: "Credenciales inválidas",
    sessionExpired: "Tu sesión ha expirado",
  },
  navigation: {
    dashboard: "Dashboard",
    agents: "Agentes",
    documents: "Documentos",
    chat: "Chat",
    playground: "Playground",
    usage: "Uso",
    billing: "Facturación",
    settings: "Configuración",
    apiKeys: "Claves API",
    tenants: "Tenants",
    analytics: "Analíticas",
    aiLab: "AI Lab",
  },
  dashboard: {
    title: "Dashboard",
    welcome: "Bienvenido",
    overview: "Vista general",
    totalAgents: "Total de Agentes",
    activeConversations: "Conversaciones Activas",
    tokensUsed: "Tokens Usados",
    documentsProcessed: "Documentos Procesados",
    recentActivity: "Actividad Reciente",
    quickActions: "Acciones Rápidas",
  },
  agents: {
    title: "Agentes",
    subtitle: "Gestiona tus agentes de IA",
    createAgent: "Crear Agente",
    editAgent: "Editar Agente",
    deleteAgent: "Eliminar Agente",
    agentName: "Nombre del agente",
    agentDescription: "Descripción",
    systemPrompt: "System Prompt",
    model: "Modelo",
    temperature: "Temperature",
    maxTokens: "Max Tokens",
    noAgents: "No tienes agentes creados",
    createFirst: "Crea tu primer agente para comenzar",
  },
  documents: {
    title: "Documentos",
    subtitle: "Base de conocimiento de tus agentes",
    uploadDocument: "Subir Documento",
    deleteDocument: "Eliminar Documento",
    processing: "Procesando",
    processed: "Procesado",
    failed: "Error",
    noDocuments: "No hay documentos",
    uploadFirst: "Sube documentos para alimentar a tus agentes",
    supportedFormats: "Formatos soportados: PDF, DOCX, TXT",
    maxSize: "Tamaño máximo: 10MB",
  },
  chat: {
    title: "Chat",
    newConversation: "Nueva conversación",
    sendMessage: "Enviar mensaje",
    typeMessage: "Escribe un mensaje...",
    clearChat: "Limpiar chat",
    exportChat: "Exportar conversación",
    noMessages: "Sin mensajes",
    startConversation: "Inicia una conversación",
  },
  billing: {
    title: "Facturación",
    subtitle: "Gestiona tu suscripción y pagos",
    currentPlan: "Plan Actual",
    changePlan: "Cambiar Plan",
    paymentMethod: "Método de Pago",
    invoices: "Facturas",
    usage: "Uso",
    nextBilling: "Próxima facturación",
    plans: {
      basic: "Básico",
      pro: "Pro",
      enterprise: "Enterprise",
    },
  },
  usage: {
    title: "Uso",
    subtitle: "Monitorea tu consumo de recursos",
    tokensUsed: "Tokens Usados",
    tokensRemaining: "Tokens Restantes",
    storageUsed: "Almacenamiento Usado",
    apiCalls: "Llamadas API",
    period: "Período",
    thisMonth: "Este mes",
    lastMonth: "Mes pasado",
  },
  settings: {
    title: "Configuración",
    general: "General",
    security: "Seguridad",
    notifications: "Notificaciones",
    apiKeys: "Claves API",
    team: "Equipo",
    danger: "Zona de Peligro",
    deleteAccount: "Eliminar cuenta",
  },
  errors: {
    generic: "Ha ocurrido un error",
    notFound: "No encontrado",
    unauthorized: "No autorizado",
    forbidden: "Acceso denegado",
    serverError: "Error del servidor",
    networkError: "Error de conexión",
    validationError: "Error de validación",
    tryAgain: "Intenta de nuevo",
  },
};

// English translations
const en: Translations = {
  common: {
    save: "Save",
    cancel: "Cancel",
    delete: "Delete",
    edit: "Edit",
    create: "Create",
    search: "Search",
    filter: "Filter",
    loading: "Loading...",
    error: "Error",
    success: "Success",
    confirm: "Confirm",
    back: "Back",
    next: "Next",
    previous: "Previous",
    yes: "Yes",
    no: "No",
    all: "All",
    none: "None",
    select: "Select",
    upload: "Upload",
    download: "Download",
    export: "Export",
    import: "Import",
    copy: "Copy",
    copied: "Copied",
    close: "Close",
    open: "Open",
    view: "View",
    details: "Details",
    actions: "Actions",
    status: "Status",
    name: "Name",
    email: "Email",
    password: "Password",
    description: "Description",
    date: "Date",
    time: "Time",
    amount: "Amount",
    total: "Total",
    active: "Active",
    inactive: "Inactive",
    pending: "Pending",
    completed: "Completed",
    failed: "Failed",
  },
  auth: {
    login: "Log in",
    logout: "Log out",
    register: "Sign up",
    forgotPassword: "Forgot your password?",
    resetPassword: "Reset password",
    emailPlaceholder: "you@email.com",
    passwordPlaceholder: "••••••••",
    loginTitle: "Welcome back",
    loginSubtitle: "Enter your credentials to continue",
    registerTitle: "Create account",
    registerSubtitle: "Start your free trial",
    invalidCredentials: "Invalid credentials",
    sessionExpired: "Your session has expired",
  },
  navigation: {
    dashboard: "Dashboard",
    agents: "Agents",
    documents: "Documents",
    chat: "Chat",
    playground: "Playground",
    usage: "Usage",
    billing: "Billing",
    settings: "Settings",
    apiKeys: "API Keys",
    tenants: "Tenants",
    analytics: "Analytics",
    aiLab: "AI Lab",
  },
  dashboard: {
    title: "Dashboard",
    welcome: "Welcome",
    overview: "Overview",
    totalAgents: "Total Agents",
    activeConversations: "Active Conversations",
    tokensUsed: "Tokens Used",
    documentsProcessed: "Documents Processed",
    recentActivity: "Recent Activity",
    quickActions: "Quick Actions",
  },
  agents: {
    title: "Agents",
    subtitle: "Manage your AI agents",
    createAgent: "Create Agent",
    editAgent: "Edit Agent",
    deleteAgent: "Delete Agent",
    agentName: "Agent name",
    agentDescription: "Description",
    systemPrompt: "System Prompt",
    model: "Model",
    temperature: "Temperature",
    maxTokens: "Max Tokens",
    noAgents: "No agents created",
    createFirst: "Create your first agent to get started",
  },
  documents: {
    title: "Documents",
    subtitle: "Knowledge base for your agents",
    uploadDocument: "Upload Document",
    deleteDocument: "Delete Document",
    processing: "Processing",
    processed: "Processed",
    failed: "Failed",
    noDocuments: "No documents",
    uploadFirst: "Upload documents to feed your agents",
    supportedFormats: "Supported formats: PDF, DOCX, TXT",
    maxSize: "Max size: 10MB",
  },
  chat: {
    title: "Chat",
    newConversation: "New conversation",
    sendMessage: "Send message",
    typeMessage: "Type a message...",
    clearChat: "Clear chat",
    exportChat: "Export conversation",
    noMessages: "No messages",
    startConversation: "Start a conversation",
  },
  billing: {
    title: "Billing",
    subtitle: "Manage your subscription and payments",
    currentPlan: "Current Plan",
    changePlan: "Change Plan",
    paymentMethod: "Payment Method",
    invoices: "Invoices",
    usage: "Usage",
    nextBilling: "Next billing",
    plans: {
      basic: "Basic",
      pro: "Pro",
      enterprise: "Enterprise",
    },
  },
  usage: {
    title: "Usage",
    subtitle: "Monitor your resource consumption",
    tokensUsed: "Tokens Used",
    tokensRemaining: "Tokens Remaining",
    storageUsed: "Storage Used",
    apiCalls: "API Calls",
    period: "Period",
    thisMonth: "This month",
    lastMonth: "Last month",
  },
  settings: {
    title: "Settings",
    general: "General",
    security: "Security",
    notifications: "Notifications",
    apiKeys: "API Keys",
    team: "Team",
    danger: "Danger Zone",
    deleteAccount: "Delete account",
  },
  errors: {
    generic: "An error occurred",
    notFound: "Not found",
    unauthorized: "Unauthorized",
    forbidden: "Access denied",
    serverError: "Server error",
    networkError: "Network error",
    validationError: "Validation error",
    tryAgain: "Try again",
  },
};

const translations: Record<Locale, Translations> = { es, en };

let currentLocale: Locale = "es";

/**
 * Set the current locale.
 */
export function setLocale(locale: Locale): void {
  currentLocale = locale;
  if (typeof window !== "undefined") {
    localStorage.setItem("locale", locale);
  }
}

/**
 * Get the current locale.
 */
export function getLocale(): Locale {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("locale") as Locale | null;
    if (stored && (stored === "es" || stored === "en")) {
      currentLocale = stored;
    }
  }
  return currentLocale;
}

/**
 * Get a translation by key path.
 *
 * @param key - Dot-separated key path (e.g., "common.save")
 * @param params - Optional parameters for interpolation
 * @returns The translated string
 */
export function t(key: string, params?: Record<string, string | number>): string {
  const keys = key.split(".");
  let value: string | Translations = translations[currentLocale];

  for (const k of keys) {
    if (typeof value === "object" && k in value) {
      value = value[k];
    } else {
      console.warn(`Translation not found: ${key}`);
      return key;
    }
  }

  if (typeof value !== "string") {
    console.warn(`Translation is not a string: ${key}`);
    return key;
  }

  // Parameter interpolation
  if (params) {
    return value.replace(/\{(\w+)\}/g, (_, param) => {
      return params[param]?.toString() ?? `{${param}}`;
    });
  }

  return value;
}

/**
 * React hook for translations.
 */
export function useTranslation() {
  return {
    t,
    locale: getLocale(),
    setLocale,
  };
}

export default { t, getLocale, setLocale, useTranslation };
