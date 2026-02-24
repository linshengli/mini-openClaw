"use client";

import { Bot, FileCode, ListChecks, MessageSquare, Sparkles } from "lucide-react";

const tabs = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "memory", label: "Memory", icon: FileCode },
  { id: "skills", label: "Skills", icon: Sparkles }
] as const;

type Props = {
  activeTab: "chat" | "memory" | "skills";
  onTabChange: (tab: "chat" | "memory" | "skills") => void;
  sessions: string[];
  sessionId: string;
  onSessionSelect: (sessionId: string) => void;
};

export function Sidebar({ activeTab, onTabChange, sessions, sessionId, onSessionSelect }: Props) {
  return (
    <aside className="frost-panel flex h-full min-h-[300px] flex-col p-4">
      <div className="mb-4 flex items-center gap-2 rounded-xl bg-accent/8 px-3 py-2 text-accent">
        <Bot className="h-4 w-4" />
        <span className="text-sm font-semibold">Agent Console</span>
      </div>

      <nav className="grid grid-cols-3 gap-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onTabChange(tab.id)}
              className={`rounded-xl border px-2 py-2 text-xs transition ${
                active
                  ? "border-accent bg-accent text-white"
                  : "border-line bg-white/80 text-ink/80 hover:border-accent/40"
              }`}
            >
              <div className="flex items-center justify-center gap-1.5">
                <Icon className="h-3.5 w-3.5" />
                <span>{tab.label}</span>
              </div>
            </button>
          );
        })}
      </nav>

      <div className="mt-6 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ink/50">
        <ListChecks className="h-3.5 w-3.5" />
        Sessions
      </div>

      <div className="scroll-thin mt-2 flex-1 space-y-2 overflow-auto pr-1">
        {sessions.length === 0 ? (
          <div className="rounded-xl border border-dashed border-line p-3 text-xs text-ink/55">
            no sessions yet
          </div>
        ) : (
          sessions.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => onSessionSelect(item)}
              className={`w-full rounded-xl border px-3 py-2 text-left text-sm transition ${
                item === sessionId
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-line bg-white/80 text-ink/80 hover:border-accent/40"
              }`}
            >
              {item}
            </button>
          ))
        )}
      </div>
    </aside>
  );
}
