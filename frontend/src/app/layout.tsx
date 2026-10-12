import type { Metadata } from "next";
import { DM_Sans, Source_Serif_4 } from "next/font/google";
import Link from "next/link";
import Image from "next/image";
import { SiteNav } from "@/components/SiteNav";
import "./globals.css";

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
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
    <html lang="en" className={`${dmSans.variable} ${sourceSerif.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col text-foreground">
        <div className="atmosphere flex min-h-full flex-col">
          <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/85 backdrop-blur-md">
            <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
              <Link href="/" className="group flex items-center gap-2.5">
                <Image src="/logo.svg" alt="" width={32} height={32} className="h-8 w-8" priority />
                <span className="font-serif text-lg font-bold tracking-tight">
                  Sajha<span className="text-teal-700">News</span>
                </span>
              </Link>
              <SiteNav />
              <Link
                href="/search"
                className="rounded-full bg-[#1a2e35] px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-[#243b44] sm:text-sm"
              >
                Search
              </Link>
            </div>
          </header>

          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">{children}</main>

          <footer className="border-t border-black/[0.06] py-8 text-center text-xs text-foreground/40">
            <p>
              © {new Date().getFullYear()} SajhaNews ·{" "}
              <Link href="/sources" className="hover:text-foreground/70">
                Sources
              </Link>
              {" · "}
              <Link href="/admin" className="hover:text-foreground/70">
                Admin
              </Link>
            </p>
          </footer>
        </div>
      </body>
    </html>
  );
}
