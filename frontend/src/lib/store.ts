import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, Agent, Conversation } from "@/types";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      logout: () => set({ user: null, isAuthenticated: false }),
    }),
    {
      name: "auth-storage",
    }
  )
);

interface ChatState {
  currentAgent: Agent | null;
  currentConversation: Conversation | null;
  messages: { role: string; content: string }[];
  isStreaming: boolean;
  setCurrentAgent: (agent: Agent | null) => void;
  setCurrentConversation: (conversation: Conversation | null) => void;
  addMessage: (message: { role: string; content: string }) => void;
  updateLastMessage: (content: string) => void;
  clearMessages: () => void;
  setIsStreaming: (streaming: boolean) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  currentAgent: null,
  currentConversation: null,
  messages: [],
  isStreaming: false,
  setCurrentAgent: (agent) => set({ currentAgent: agent }),
  setCurrentConversation: (conversation) =>
    set({
      currentConversation: conversation,
      messages: conversation?.messages.map((m) => ({ role: m.role, content: m.content })) || [],
    }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  updateLastMessage: (content) =>
    set((state) => {
      const messages = [...state.messages];
      if (messages.length > 0) {
        messages[messages.length - 1].content += content;
      }
      return { messages };
    }),
  clearMessages: () => set({ messages: [], currentConversation: null }),
  setIsStreaming: (streaming) => set({ isStreaming: streaming }),
}));

interface UIState {
  sidebarOpen: boolean;
  theme: "light" | "dark";
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: "light" | "dark") => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: "light",
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: "ui-storage",
    }
  )
);
