import { Marked } from "marked";
import { P, matcher } from "@/lib/glossary-server";
import { repoText } from "@/lib/data";
import { linkifyHtml } from "@/lib/linkify";
import { NotAvailable } from "@/components/ui";

export const metadata = { title: "Agent demo · Complex priors" };

const escapeHtml = (t: string) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

export default function AgentDemo() {
  const t = repoText("demo/agent_session.md");
  let html = "";
  if (t.ok) {
    const md = new Marked({ gfm: true });
    // Raw HTML inside the transcript is shown as text, never injected.
    md.use({ renderer: { html: (tok: { text: string }) => escapeHtml(tok.text) } });
    html = linkifyHtml(md.parse(t.data, { async: false }) as string, matcher);
  }
  return (
    <div>
      <h1 className="h1">Agent demo</h1>
      <P>
        A recorded session in which an AI agent answers a biology question using only this project&apos;s MCP tools. The transcript
        below is rendered from the markdown file at build time.
      </P>
      <p className="mt-1 font-mono text-[11px] text-muted">source: {t.file}</p>
      {t.ok ? (
        <article className="md mt-4 max-w-3xl break-words" dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        <NotAvailable what="Agent session transcript" file={t.file} reason={t.reason} />
      )}
    </div>
  );
}
