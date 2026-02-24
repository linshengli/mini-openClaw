const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8002";

export type ChatEvent = { type: string; value: string };

export async function listSessions(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/sessions`, { cache: "no-store" });
  if (!res.ok) throw new Error(`list sessions failed: ${res.status}`);
  const data = (await res.json()) as { sessions: string[] };
  return data.sessions;
}

export async function readFile(path: string): Promise<string> {
  const url = new URL(`${API_BASE}/api/files`);
  url.searchParams.set("path", path);
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`read file failed: ${res.status}`);
  const data = (await res.json()) as { content: string };
  return data.content;
}

export async function writeFile(path: string, content: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/files`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, content })
  });
  if (!res.ok) throw new Error(`write file failed: ${res.status}`);
}

export async function chatSSE(
  sessionId: string,
  message: string,
  onEvent: (event: ChatEvent) => void
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, stream: true })
  });

  if (!res.ok || !res.body) {
    throw new Error(`chat failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const line = chunk
        .split("\n")
        .map((l) => l.trim())
        .find((l) => l.startsWith("data:"));
      if (!line) continue;
      const payload = line.slice(5).trim();
      try {
        const event = JSON.parse(payload) as ChatEvent;
        onEvent(event);
      } catch {
        onEvent({ type: "error", value: `bad event: ${payload}` });
      }
    }
  }
}
