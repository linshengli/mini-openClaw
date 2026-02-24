"use client";

import dynamic from "next/dynamic";
import { Save } from "lucide-react";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

type Props = {
  targetPath: string;
  content: string;
  loading: boolean;
  saving: boolean;
  onPathChange: (path: string) => void;
  onContentChange: (content: string) => void;
  onLoad: () => void;
  onSave: () => void;
};

export function FileInspector({
  targetPath,
  content,
  loading,
  saving,
  onPathChange,
  onContentChange,
  onLoad,
  onSave
}: Props) {
  return (
    <section className="frost-panel flex h-full min-h-[420px] flex-col p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-xl leading-none text-ink">Inspector</h2>
        <button
          type="button"
          onClick={onSave}
          disabled={saving || loading}
          className="inline-flex items-center gap-1 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-white hover:bg-accent2 disabled:opacity-60"
        >
          <Save className="h-3.5 w-3.5" />
          {saving ? "保存中" : "保存"}
        </button>
      </div>

      <div className="mb-2 grid grid-cols-[1fr_auto] gap-2">
        <input
          value={targetPath}
          onChange={(e) => onPathChange(e.target.value)}
          className="rounded-xl border border-line bg-white/85 px-3 py-2 text-sm outline-none focus:border-accent"
          placeholder="backend/memory/MEMORY.md"
        />
        <button
          type="button"
          onClick={onLoad}
          disabled={loading}
          className="rounded-xl border border-line bg-white/85 px-3 py-2 text-xs font-semibold text-ink/80 hover:border-accent/50"
        >
          {loading ? "读取中" : "读取"}
        </button>
      </div>

      <div className="min-h-[340px] flex-1 overflow-hidden rounded-xl border border-line">
        <MonacoEditor
          language="markdown"
          value={content}
          onChange={(v) => onContentChange(v ?? "")}
          theme="vs"
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: "on",
            wordWrap: "on",
            smoothScrolling: true,
            scrollBeyondLastLine: false
          }}
        />
      </div>
    </section>
  );
}
