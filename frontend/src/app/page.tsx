"use client";

import { useEffect, useMemo, useState } from "react";

import { ChatStage, type ChatMessage } from "../components/chat/chat-stage";
import { FileInspector } from "../components/editor/file-inspector";
import { Sidebar } from "../components/layout/sidebar";
import { TopBar } from "../components/layout/top-bar";
import { chatSSE, listSessions, readFile, writeFile, type ChatEvent } from "../lib/api";

type TabKey = "chat" | "memory" | "skills";

const DEFAULT_MEMORY = "backend/memory/MEMORY.md";
const DEFAULT_SKILL = "backend/skills/get_weather/SKILL.md";

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<TabKey>("chat");
  const [sessions, setSessions] = useState<string[]>([]);
  const [sessionId, setSessionId] = useState("main_session");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [debugOpen, setDebugOpen] = useState(true);
  const [debugEvents, setDebugEvents] = useState<ChatEvent[]>([]);

  const [path, setPath] = useState(DEFAULT_MEMORY);
  const [content, setContent] = useState("");
  const [reading, setReading] = useState(false);
  const [saving, setSaving] = useState(false);

  const inspectedPath = useMemo(() => {
    if (activeTab === "memory") return DEFAULT_MEMORY;
    if (activeTab === "skills") return DEFAULT_SKILL;
    return path;
  }, [activeTab, path]);

  useEffect(() => {
    listSessions()
      .then(setSessions)
      .catch(() => setSessions(["main_session"]));
  }, []);

  useEffect(() => {
    setPath(inspectedPath);
    void loadTarget(inspectedPath);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inspectedPath]);

  async function loadTarget(target: string) {
    try {
      setReading(true);
      const text = await readFile(target);
      setContent(text);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "load failed";
      setContent(`# load error\n\n${msg}`);
    } finally {
      setReading(false);
    }
  }

  async function sendChat() {
    const prompt = input.trim();
    if (!prompt || loading) return;

    setLoading(true);
    setDebugEvents([]);
    const userMsg: ChatMessage = { id: `${Date.now()}-u`, role: "user", content: prompt };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    try {
      await chatSSE(sessionId, prompt, (event) => {
        setDebugEvents((prev) => [...prev, event]);
        if (event.type === "final") {
          setMessages((prev) => [
            ...prev,
            { id: `${Date.now()}-a`, role: "assistant", content: event.value }
          ]);
          listSessions().then(setSessions).catch(() => undefined);
        }
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "chat failed";
      setMessages((prev) => [...prev, { id: `${Date.now()}-e`, role: "assistant", content: msg }]);
    } finally {
      setLoading(false);
    }
  }

  async function saveTarget() {
    try {
      setSaving(true);
      await writeFile(path, content);
      setDebugEvents((prev) => [...prev, { type: "save", value: `saved ${path}` }]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "save failed";
      setDebugEvents((prev) => [...prev, { type: "error", value: msg }]);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen">
      <TopBar />
      <main className="mx-auto max-w-[1800px] px-3 pb-4 pt-20 sm:px-6 sm:pb-6">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[270px_1.2fr_1fr]">
          <Sidebar
            activeTab={activeTab}
            onTabChange={setActiveTab}
            sessions={sessions}
            sessionId={sessionId}
            onSessionSelect={setSessionId}
          />

          <ChatStage
            messages={messages}
            input={input}
            loading={loading}
            debugOpen={debugOpen}
            debugEvents={debugEvents}
            onInputChange={setInput}
            onSend={sendChat}
            onToggleDebug={() => setDebugOpen((v) => !v)}
          />

          <FileInspector
            targetPath={path}
            content={content}
            loading={reading}
            saving={saving}
            onPathChange={setPath}
            onContentChange={setContent}
            onLoad={() => loadTarget(path)}
            onSave={saveTarget}
          />
        </div>
      </main>
    </div>
  );
}
