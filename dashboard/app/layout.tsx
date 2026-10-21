import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { GlossaryProvider } from "@/components/GlossaryProvider";
import { glossary } from "@/lib/glossary-server";

export const metadata: Metadata = {
  title: "Complex priors for single-cell proteomics",
  description: "Benchmark dashboard for scp-graphfs-mcp: do curated protein-complex priors help reconstruct single-cell protein measurements?",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f7f7f5" },
    { media: "(prefers-color-scheme: dark)", color: "#121211" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg font-sans text-ink antialiased">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-surface focus:p-2">
          Skip to content
        </a>
        <header className="sticky top-0 z-30 border-b border-line bg-bg/95 backdrop-blur">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3">
            <Link href="/" className="min-w-0 truncate font-semibold text-ink">
              scp-graphfs-mcp
            </Link>
            <Nav />
          </div>
        </header>
        <main id="main" className="mx-auto max-w-5xl px-4 pb-16 pt-6">
          {children}
        </main>
        <footer className="border-t border-line">
          <div className="mx-auto max-w-5xl px-4 py-6 text-xs text-muted">
            Static build. All result numbers are read from files at build time. Underlined terms open the glossary
            {glossary.entries ? ` (${glossary.entries.length} terms from ${glossary.file})` : ` (${glossary.file}: not available yet)`}.
          </div>
        </footer>
        <GlossaryProvider entries={glossary.entries} basePath={process.env.NEXT_BASE_PATH || ""} />
      </body>
    </html>
  );
}
