"use client";

import ReactMarkdown from "react-markdown";
import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatMessageProps {
  role: "user" | "assistant" | "system";
  content: string;
  isStreaming?: boolean;
}

export function ChatMessage({ role, content, isStreaming }: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div className={cn("flex gap-4 p-4", isUser ? "bg-white" : "bg-gray-50")}>
      <div
        className={cn(
          "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
          isUser ? "bg-primary-100" : "bg-gray-200"
        )}
      >
        {isUser ? (
          <User className="w-5 h-5 text-primary-700" />
        ) : (
          <Bot className="w-5 h-5 text-gray-700" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-gray-500 mb-1">
          {isUser ? "Tú" : "Asistente"}
        </p>
        <div className="prose prose-sm max-w-none text-gray-900">
          <ReactMarkdown>{content}</ReactMarkdown>
          {isStreaming && (
            <span className="inline-block w-2 h-4 bg-primary-500 animate-pulse ml-1" />
          )}
        </div>
      </div>
    </div>
  );
}
