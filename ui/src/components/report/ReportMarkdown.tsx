import ReactMarkdown, { type Components } from 'react-markdown';
import { cn } from '@/lib/utils/cn';

// Tight markdown styling so LLM output inherits our theme. No raw HTML.
const components: Components = {
  p: ({ node: _node, ...props }) => (
    <p className="leading-relaxed [&:not(:last-child)]:mb-2" {...props} />
  ),
  ul: ({ node: _node, ...props }) => (
    <ul className="ml-5 list-disc space-y-1" {...props} />
  ),
  ol: ({ node: _node, ...props }) => (
    <ol className="ml-5 list-decimal space-y-1" {...props} />
  ),
  strong: ({ node: _node, ...props }) => (
    <strong className="font-semibold text-foreground" {...props} />
  ),
  em: ({ node: _node, ...props }) => <em className="italic" {...props} />,
  a: ({ node: _node, ...props }) => (
    <a
      className="text-primary underline-offset-2 hover:underline"
      target="_blank"
      rel="noreferrer noopener"
      {...props}
    />
  ),
  code: ({ node: _node, ...props }) => (
    <code className="rounded bg-muted px-1 py-0.5 text-[0.85em]" {...props} />
  ),
};

interface ReportMarkdownProps {
  children: string;
  className?: string;
}

export function ReportMarkdown({ children, className }: ReportMarkdownProps) {
  return (
    <div className={cn('text-sm text-foreground/90', className)}>
      <ReactMarkdown
        components={components}
        disallowedElements={['script', 'iframe', 'style']}
        skipHtml
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
