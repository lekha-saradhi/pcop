import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Geist_Mono } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import { AuthProvider } from "@/hooks/useAuth";
import ConditionalShell from "@/components/ConditionalShell";

const jakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
  weight: ['400', '500', '600', '700', '800'],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PCOP · NextGenHacks 2026",
  description: "Predictive Customer Outreach Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={cn("h-full antialiased", jakarta.variable, geistMono.variable)}>
      <body className="min-h-full flex bg-[#F4F6F9] text-slate-900 font-sans">
        <AuthProvider>
          <ConditionalShell>
            {children}
          </ConditionalShell>
        </AuthProvider>
      </body>
    </html>
  );
}
