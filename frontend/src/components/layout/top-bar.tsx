export function TopBar() {
  return (
    <header className="fixed inset-x-0 top-0 z-40 px-3 py-3 sm:px-6">
      <div className="frost-panel mx-auto flex h-12 w-full max-w-[1800px] items-center justify-between px-4 sm:px-6">
        <div className="text-sm font-medium tracking-wide text-ink/80">mini OpenClaw</div>
        <a
          className="text-sm font-semibold text-accent transition hover:text-accent2"
          href="https://fufan.ai"
          target="_blank"
          rel="noreferrer"
        >
          赋范空间
        </a>
      </div>
    </header>
  );
}
