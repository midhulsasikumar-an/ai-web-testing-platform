"use client";

import { useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function AIAssistantPage() { 
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I am your AI Testing Assistant.",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);

    const currentInput = input;
    setInput("");
    setLoading(true);

    try {
        const response = await fetch("http://127.0.0.1:8000/ai/chat", {
            method: "POST",
            headers: {
            "Content-Type": "application/json",
            },
            body: JSON.stringify({
            message: currentInput,
            }),
        });

        const data = await response.json();

        const aiMessage: Message = {
            role: "assistant",
            content: data.response,
        };

        setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
        console.error(error);

        const errorMessage: Message = {
            role: "assistant",
            content: "Error connecting to AI backend.",
        };

        setMessages((prev) => [...prev, errorMessage]);
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      {/* Header */}
      <div className="border-b border-zinc-800 p-4 text-xl font-semibold">
        AI Testing Assistant
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`max-w-[80%] rounded-2xl px-4 py-3 ${
              msg.role === "user"
                ? "ml-auto bg-blue-600"
                : "bg-zinc-800"
            }`}
          >
            {msg.content}
          </div>
        ))}

        {loading && (
          <div className="bg-zinc-800 rounded-2xl px-4 py-3 w-fit">
            Thinking...
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-zinc-800 p-4 flex gap-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the AI to test something..."
          className="flex-1 bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3 outline-none"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              sendMessage();
            }
          }}
        />

        <button
          onClick={sendMessage}
          className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-xl font-medium"
        >
          Send
        </button>
      </div>
    </div>
  );
}