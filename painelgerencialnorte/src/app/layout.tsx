import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Painel Gerencial Norte",
  description: "Painel comercial SaaS da Equipe Norte",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className="h-full">
      <body className="min-h-full antialiased">{children}</body>
    </html>
  );
}
