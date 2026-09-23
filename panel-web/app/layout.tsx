import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Space_Grotesk } from "next/font/google";
import "./globals.css";

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-plus-jakarta",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Actuariosa — Panel de Monitoreo Gerencial",
  description:
    "Supervisión ejecutiva en tiempo real del inventario de correos, depuración de empresas Supercias, rendimiento de campañas B2B y prospectos comerciales.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
    apple: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className={`light ${plusJakarta.variable} ${spaceGrotesk.variable}`}>
      <body className="bg-[#f8fafc] text-slate-900 antialiased min-h-screen selection:bg-[#262478]/15 selection:text-[#262478] font-sans">
        {children}
      </body>
    </html>
  );
}
