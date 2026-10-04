/**
 * Minimal Markdown renderer for agent artifacts.
 *
 * Deliberately hand-rolled rather than pulling a parser: artifacts only ever
 * use headings, bold, italics, lists and paragraphs, and all input is escaped
 * before any formatting is applied.
 */

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function inline(text: string): string {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}

export function Markdown({ source }: { source: string }) {
  const lines = source.split("\n");
  const blocks: string[] = [];
  let listBuffer: string[] = [];
  let listType: "ul" | "ol" | null = null;

  const flushList = () => {
    if (listBuffer.length && listType) {
      blocks.push(`<${listType}>${listBuffer.join("")}</${listType}>`);
    }
    listBuffer = [];
    listType = null;
  };

  for (const raw of lines) {
    const line = raw.trimEnd();

    const heading = /^(#{1,4})\s+(.*)$/.exec(line);
    if (heading) {
      flushList();
      const level = heading[1].length;
      blocks.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      continue;
    }

    const bullet = /^[-*]\s+(.*)$/.exec(line);
    if (bullet) {
      if (listType !== "ul") flushList();
      listType = "ul";
      listBuffer.push(`<li>${inline(bullet[1])}</li>`);
      continue;
    }

    const numbered = /^\d+\.\s+(.*)$/.exec(line);
    if (numbered) {
      if (listType !== "ol") flushList();
      listType = "ol";
      listBuffer.push(`<li>${inline(numbered[1])}</li>`);
      continue;
    }

    if (!line.trim()) {
      flushList();
      continue;
    }

    flushList();
    blocks.push(`<p>${inline(line)}</p>`);
  }
  flushList();

  return (
    <div
      className="markdown-body"
      // Safe: every path above escapes before formatting; no raw HTML survives.
      dangerouslySetInnerHTML={{ __html: blocks.join("") }}
    />
  );
}
