"use client";

import { useState } from "react";
import { Send, Bot, User } from "lucide-react";

export type Message = {
  id: string;
  sender: "USER" | "AI ASSISTANT";
  text: string;
};

type AiChatProps = {
  messages: Message[];
  onSendMessage: (text: string) => void;
  isLoading: boolean;
};

export function AiChat({ messages, onSendMessage, isLoading }: AiChatProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim());
      setInput("");
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 border-r border-gray-200">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-2">
            <Bot className="w-12 h-12 text-gray-300" />
            <p>What are you looking for today?</p>
            <p className="text-sm italic text-gray-400">Try: "Find me a gaming mouse under ₹3000"</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${
                msg.sender === "USER" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                  msg.sender === "USER"
                    ? "bg-indigo-600 text-white rounded-br-none"
                    : "bg-white border border-gray-200 text-gray-800 rounded-bl-none shadow-sm"
                }`}
              >
                <div className="flex items-center space-x-2 mb-1">
                  {msg.sender === "USER" ? (
                    <User className="w-4 h-4 opacity-75" />
                  ) : (
                    <Bot className="w-4 h-4 text-indigo-500" />
                  )}
                  <span className="text-xs font-medium opacity-75">
                    {msg.sender}
                  </span>
                </div>
                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                  {msg.text}
                </p>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
              <div className="flex space-x-1.5 items-center h-5">
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce"></div>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 bg-white border-t border-gray-200">
        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your request here..."
            disabled={isLoading}
            className="w-full pl-4 pr-12 py-3 rounded-xl border border-gray-300 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-shadow disabled:bg-gray-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-indigo-600 hover:bg-indigo-50 rounded-lg disabled:opacity-50 disabled:hover:bg-transparent transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
}
