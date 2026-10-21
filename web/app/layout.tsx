import type { Metadata } from 'next';
import SiteHeader from './components/site-header';
import './globals.css';
import './workspaces.css';
export const metadata:Metadata={title:'FrailtyScope | Ageing & Health Intelligence',description:'Research demo for explainable frailty modeling, with fictional patient cases. Not for clinical use.',robots:{index:false,follow:false}};
export default function RootLayout({children}:{children:React.ReactNode}){
 return <html lang="en"><body><SiteHeader/>{children}<footer className="site-footer"><span>© 2026 FrailtyScope · Independent research demonstration</span><span>Synthetic data only · Not a medical device</span></footer></body></html>;
}
