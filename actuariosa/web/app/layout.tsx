import type { Metadata } from 'next';
import { Geist } from 'next/font/google';
import './globals.css';
const geist = Geist({variable:'--font-geist-sans',subsets:['latin']});
const title='Actuariosa | Certeza para el futuro de tu empresa';
const description='Estudios actuariales de jubilación patronal y desahucio, asientos contables e impuestos diferidos. Actuarios del Ecuador.';
const origin = process.env.VERCEL_PROJECT_PRODUCTION_URL
  ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
  : 'https://actuariosa-empresa.esoria-contact.chatgpt.site';
export const metadata: Metadata = {title,description,icons:{icon:'/favicon.svg'},robots:{index:false,follow:false},openGraph:{title,description,type:'website',locale:'es_EC',siteName:'Actuariosa',url:origin,images:[{url:`${origin}/og.png`,width:1536,height:1024,alt:'Actuariosa: El futuro de tu empresa merece certeza.'}]},twitter:{card:'summary_large_image',title,description,images:[`${origin}/og.png`]}};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="es"><body className={geist.variable}>{children}</body></html>}

