import '../globals.css';
import '../nhanes.css';
import '../nhanes-v11.css';
import '../nhanes-v12.css';
import '../engine-studio-v32.css';
import '../engine-studio-v33.css';
import '../engine-studio-v34.css';
import '../doctor-v35.css';
import '../doctor-journey-v36.css';
import '../inference-v37.css';
import '../inference-v38.css';
import '../inference-v39.css';
import '../inference-serving-v40.css';
import '../validation-v41.css';
import '../translation-v42.css';
import '../artifact-v43.css';
import '../study-handoff-v44.css';

// Earlier workspaces, kept for the record and for their regression tests.
// Their styles load only under /archive so they cannot affect the main product.
export default function ArchiveLayout({children}: {children: React.ReactNode}) {
  return <>{children}</>;
}
