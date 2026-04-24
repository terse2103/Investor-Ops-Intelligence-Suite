import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Investor Ops & Intelligence Suite",
  description:
    "AI-powered mutual fund Q&A, weekly product pulse, and voice-enabled advisor booking — all in one fintech ops suite.",
  keywords: ["mutual funds", "INDMoney", "RAG chatbot", "investor operations"],
  openGraph: {
    title: "Investor Ops & Intelligence Suite",
    description: "Facts-only MF chatbot · Weekly pulse · Voice advisor booking",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
