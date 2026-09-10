import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import Image from "next/image";
import { Search, Compass, Shield, Layers, RefreshCw, Radio } from "lucide-react";
import { DevelopmentNoteDialog } from "@/components/DevelopmentNoteDialog";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SajhaNews — See Every Side of Nepal's News",
  description:
    "Aggregating 30+ Nepali and international news publishers with media bias ratings and multi-perspective coverage comparison.",
  icons: {
    icon: "/Logo.png",
    shortcut: "/Logo.png",
    apple: "/Logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-background text-foreground selection:bg-blue-500/20 selection:text-blue-400">
        {/* Main Sticky Navbar */}
        <header className="sticky top-0 z-50 bg-surface/85 backdrop-blur-xl border-b border-border">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
            {/* Logo */}
            <div className="flex items-center gap-6">
              <Link href="/" className="flex items-center gap-2.5 group">
                <Image
                  src="/Logo.png"
                  alt="SajhaNews Logo"
                  width={34}
                  height={34}
                  className="h-8 w-auto object-contain group-hover:scale-105 transition-transform shrink-0"
                  priority
                />
                <div>
                  <span className="font-extrabold text-xl tracking-tight text-foreground group-hover:text-blue-400 transition-colors">
                    Sajha<span className="text-blue-500">News</span>
                  </span>
                  <div className="flex gap-0.5 mt-0.5 w-16 h-1 rounded-full overflow-hidden">
                    <div className="w-1/3 bg-blue-500" />
                    <div className="w-1/3 bg-slate-400" />
                    <div className="w-1/3 bg-red-500" />
                  </div>
                </div>
              </Link>
            </div>

            {/* Right actions */}
            <div className="flex items-center gap-2 sm:gap-3">
              <DevelopmentNoteDialog />
              <Link
                href="/admin"
                className="hidden sm:flex items-center gap-1.5 text-xs font-semibold text-foreground/70 hover:text-white px-3 py-2 rounded-lg border border-border hover:border-blue-500/50 hover:bg-surface-hover transition-all"
              >
                <Layers size={13} className="text-blue-400" />
                <span>Admin Dashboard</span>
              </Link>
              <Link
                href="/"
                className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg font-semibold text-xs transition-colors shadow-lg shadow-blue-500/20 flex items-center gap-1.5"
              >
                <Radio size={13} />
                <span>Live Feed</span>
              </Link>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 w-full bg-background">
          <div className="max-w-7xl mx-auto px-4 sm:px-6">
            {children}
          </div>
        </main>

        {/* Ground News Inspired Footer */}
        <footer className="border-t border-border bg-surface/50 mt-16 text-foreground/60 text-xs">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
              <div className="space-y-3 md:col-span-2">
                <div className="flex items-center gap-2.5">
                  <Image
                    src="/Logo.png"
                    alt="SajhaNews Logo"
                    width={28}
                    height={28}
                    className="h-7 w-auto object-contain shrink-0"
                  />
                  <span className="font-bold text-base text-foreground">
                    Sajha<span className="text-blue-500">News</span>
                  </span>
                </div>
                <p className="max-w-md text-foreground/60 leading-relaxed">
                  SajhaNews is an open, transparent news aggregator inspired by Ground News. We index articles from over 30 leading Nepali and international portals so you can see how stories are framed from every political perspective.
                </p>
                <div className="flex items-center gap-2 pt-2">
                  <span className="text-[10px] font-bold px-2 py-1 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    Left Lean
                  </span>
                  <span className="text-[10px] font-bold px-2 py-1 rounded bg-slate-500/10 text-slate-300 border border-slate-500/20">
                    Center Balance
                  </span>
                  <span className="text-[10px] font-bold px-2 py-1 rounded bg-red-500/10 text-red-400 border border-red-500/20">
                    Right Lean
                  </span>
                </div>
              </div>

              <div>
                <h4 className="font-bold text-foreground text-sm mb-3">Coverage & Topics</h4>
                <ul className="space-y-2">
                  <li><Link href="/?topic=Nepal" className="hover:text-blue-400 transition-colors">Nepal News</Link></li>
                  <li><Link href="/?topic=Politics" className="hover:text-blue-400 transition-colors">Politics & Parliament</Link></li>
                  <li><Link href="/?topic=Business" className="hover:text-blue-400 transition-colors">Economy & Finance</Link></li>
                  <li><Link href="/?topic=Sports" className="hover:text-blue-400 transition-colors">Sports Coverage</Link></li>
                  <li><Link href="/?topic=World" className="hover:text-blue-400 transition-colors">Global Headlines</Link></li>
                </ul>
              </div>

              <div>
                <h4 className="font-bold text-foreground text-sm mb-3">Platform & Admin</h4>
                <ul className="space-y-2">
                  <li><Link href="/admin" className="hover:text-blue-400 transition-colors">Manage Portals</Link></li>
                  <li><Link href="/admin" className="hover:text-blue-400 transition-colors">Trigger Manual Crawl</Link></li>
                  <li><Link href="/admin" className="hover:text-blue-400 transition-colors">API Diagnostics</Link></li>
                  <li><a href="https://api.sajhanews.yagyatech.com.np/docs" target="_blank" rel="noreferrer" className="hover:text-blue-400 transition-colors">FastAPI Docs ↗</a></li>
                </ul>
              </div>
            </div>

            <div className="pt-8 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4 text-foreground/40">
              <p>© {new Date().getFullYear()} SajhaNews. Fair use aggregation for media literacy.</p>
              <p className="flex items-center gap-1.5">
                <span>Built for unbiased journalism in Nepal</span>
                <span>•</span>
                <span>30+ RSS feeds</span>
              </p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
