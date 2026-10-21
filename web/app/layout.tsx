import type { Metadata } from 'next';
import SiteHeader from './components/site-header';
import './globals.css';
import './nhanes.css';
export const metadata:Metadata={title:'FrailtyScope | Real-Data Ageing Research',description:'Aggregate NHANES ageing research metrics. Not a patient prediction service, not HUNT, not for clinical use.',robots:{index:false,follow:false}};
export default function RootLayout({children}:{children:React.ReactNode}){
 return <html lang="en"><body><SiteHeader/>{children}<footer className="site-footer"><span>© 2026 FrailtyScope · Independent research demonstration</span><span>Real NHANES public-use aggregate results · No individual records · Not a medical device</span></footer></body></html>;
}
