import type {Metadata} from 'next';
import SiteHeader from './components/site-header';
import './globals.css';
import './nhanes.css';
import './nhanes-v11.css';
import './nhanes-v12.css';
import './engine-studio-v32.css';
export const metadata:Metadata={title:'FrailtyScope | Ageing & Health Intelligence',description:'Clinical assessments and NHANES observational research results.',robots:{index:false,follow:false}};
export default function RootLayout({children}:{children:React.ReactNode}){
 return <html lang="en"><body><SiteHeader/>{children}<footer className="site-footer"><span>© 2026 FrailtyScope · Ageing & Health Intelligence</span><span>NHANES observational research · Aggregate results only</span></footer></body></html>;
}
