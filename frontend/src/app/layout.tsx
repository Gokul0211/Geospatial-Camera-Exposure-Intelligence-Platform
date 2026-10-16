import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { SITE_URL } from "@/lib/api/config";
import { Providers } from "@/components/providers";
import "@/styles/globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "COBRA-WATCH", template: "%s | COBRA-WATCH" },
  description: "COBRA-WATCH scores exposed cameras on how vulnerable they are and whether their feed is still real.",
  icons: { icon: "/favicon.svg" },
};

export const viewport: Viewport = { themeColor: "#0A0C0B", colorScheme: "dark" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body>
        <noscript>
          <style>{".pending-reveal{opacity:1!important}"}</style>
        </noscript>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <Providers>{children}</Providers>
        <div className="grain" aria-hidden="true" />
      </body>
    </html>
  );
}
