import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import type { ReactNode } from "react";

import favicon from "../../assets/logos/favicon.png";
import { ApiKeyBanner } from "@/components/layout/ApiKeyBanner";
import { AppHeader } from "@/components/layout/AppHeader";
import { AppSidebar } from "@/components/layout/AppSidebar";

import "./globals.css";
import { Providers } from "./providers";

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

export const metadata: Metadata = {
  title: { default: "OpenGrader Console", template: "%s · OpenGrader" },
  description: "Operate automated grading jobs and review annotated PDF submissions.",
  icons: {
    icon: favicon.src,
    apple: favicon.src
  }
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html data-scroll-behavior="smooth" lang="en" suppressHydrationWarning>
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans`}>
        <Providers>
          <AppSidebar />
          <div className="min-h-screen pb-20 md:pb-0 md:pl-64">
            <AppHeader />
            <ApiKeyBanner />
            <main className="mx-auto w-full max-w-[1600px] px-4 py-7 sm:px-6 lg:px-10 lg:py-10">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
