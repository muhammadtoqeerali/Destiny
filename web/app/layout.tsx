import type {Metadata} from 'next';
import SiteHeader from './components/site-header';
import './globals.css';
import './nhanes.css';
import './nhanes-v11.css';
import './nhanes-v12.css';
import './engine-studio-v32.css';
import './engine-studio-v33.css';
import './engine-studio-v34.css';
import './doctor-v35.css';
import './doctor-journey-v36.css';
import './inference-v37.css';
import './inference-v38.css';
import './inference-v39.css';
import './inference-serving-v40.css';
import './validation-v41.css';
import './translation-v42.css';
import './artifact-v43.css';
import './study-handoff-v44.css';
import './interview-focus-v47.css';
export const metadata:Metadata={title:'FrailtyScope | Ageing & Health Intelligence',description:'Clinical assessments and NHANES observational research results.',robots:{index:false,follow:false}};
export default function RootLayout({children}:{children:React.ReactNode}){
 return <html lang="en"><body><SiteHeader/>{children}<footer className="site-footer"><span>© 2026 FrailtyScope · Ageing & Health Intelligence</span><span>NHANES observational research · Aggregate results only</span></footer></body></html>;
}
