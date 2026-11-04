import type { Metadata } from "next";
import { Source_Sans_3, Source_Serif_4 } from "next/font/google";
import Link from "next/link";
import { SiteNav } from "@/components/SiteNav";
import "./globals.css";

const sourceSans = Source_Sans_3({
  variable: "--font-source-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const sourceSerif = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
  weight: ["600", "700"],
});

export const metadata: Metadata = {
  title: "SajhaNews",
  description: "See how Nepali and international outlets cover the same stories.",
  icons: { icon: "/logo.svg", shortcut: "/logo.svg", apple: "/logo.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${sourceSans.variable} ${sourceSerif.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <header className="border-b border-foreground bg-background">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="flex flex-wrap items-baseline justify-between gap-x-8 gap-y-1 pt-6">
              <Link
                href="/"
                className="font-serif text-[2.05rem] font-semibold leading-none tracking-tight whitespace-nowrap"
              >
                <span className="text-accent">S</span>ajhaNews
              </Link>
              <p className="text-sm text-foreground/60">Nepal coverage, compared</p>
            </div>
            <div className="mt-3 h-px w-10 bg-accent" aria-hidden="true" />
            <SiteNav />
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">{children}</main>

        <footer className="border-t border-foreground/20 py-6 text-center text-xs text-foreground/55">
          <p>
            © {new Date().getFullYear()} SajhaNews
            {" · "}
            <Link
              href="/sources"
              className="underline decoration-foreground/30 underline-offset-2 hover:text-foreground"
            >
              Sources
            </Link>
            {" · "}
            <Link
              href="/admin"
              className="underline decoration-foreground/30 underline-offset-2 hover:text-foreground"
            >
              Admin
            </Link>
          </p>
        </footer>
      </body>
    </html>
  );
}
