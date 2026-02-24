"use client";

import { useMemo } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type DebugEvent = {
  type: string;
  value: string;
};

type Props = {
  messages: ChatMessage[];
  input: string;
  loading: boolean;
  debugOpen: boolean;
  debugEvents: DebugEvent[];
  onInputChange: (value: string) => void;
  onSend: () => void;
  onToggleDebug: () => void;
};

export function ChatStage({
  messages,
  input,
  loading,
  debugOpen,
  debugEvents,
  onInputChange,
  onSend,
  onToggleDebug
}: Props) {
  const list = useMemo(() => messages, [messages]);

  return (
    <section className="frost-panel flex h-full min-h-[460px] flex-col p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-xl leading-none text-ink">Conversation</h2>
        <button
          type="button"
          onClick={onToggleDebug}
          className="flex items-center gap-1 rounded-lg border border-line bg-white/70 px-2 py-1 text-xs text-ink/70"
        >
          <span>Thought Stream</span>
          {debugOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>
      </div>

      {debugOpen ? (
        <div className="scroll-thin mb-3 max-h-28 overflow-auto rounded-xl border border-dashed border-line bg-white/70 p-2">
          {debugEvents.length === 0 ? (
            <p className="text-xs text-ink/50">暂无调试事件</p>
          ) : (
            <ul className="space-y-1 text-xs text-ink/70">
              {debugEvents.map((event, idx) => (
                <li key={`${event.type}-${idx}`}>
                  <span className="font-semibold text-accent">[{event.type}]</span> {event.value}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}

      <div className="scroll-thin flex-1 space-y-3 overflow-auto pr-1">
        {list.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-line bg-white/70 p-4 text-sm text-ink/55">
            发送第一条消息开始会话。
          </div>
        ) : (
          list.map((msg) => (
            <article
              key={msg.id}
              className={`rounded-2xl border px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "ml-8 border-accent/30 bg-accent/10 text-ink"
                  : "mr-8 border-line bg-white/85 text-ink/90"
              }`}
            >
              <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-ink/45">{msg.role}</div>
              <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
            </article>
          ))
        )}
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto]">
        <textarea
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="输入你的任务，例如：查询北京天气并记录到 MEMORY"
          className="h-20 resize-none rounded-xl border border-line bg-white/85 px-3 py-2 text-sm text-ink outline-none focus:border-accent"
        />
        <button
          type="button"
          onClick={onSend}
          disabled={loading || !input.trim()}
          className="rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent2 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "运行中..." : "发送"}
        </button>
      </div>
    </section>
  );
}
