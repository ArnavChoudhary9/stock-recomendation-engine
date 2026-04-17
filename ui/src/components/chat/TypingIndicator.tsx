export function TypingIndicator() {
  return (
    <span className="inline-flex items-center gap-1" aria-label="Assistant is typing">
      <Dot delay="0ms" />
      <Dot delay="150ms" />
      <Dot delay="300ms" />
    </span>
  );
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="size-1.5 rounded-full bg-muted-foreground/70"
      style={{
        animation: 'pulse 1s ease-in-out infinite',
        animationDelay: delay,
      }}
    />
  );
}
