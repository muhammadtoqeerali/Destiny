import type {Metadata} from 'next';
import {PopulationHero, ModelGlance} from '../ui/population';
import {ProfileExplorer} from '../ui/profile-explorer';
import {Disclosure} from '../ui/disclosure';
import mobility from '../data/real-mobility-summary-v49.json';

export const metadata: Metadata = {title: 'Doctor · FrailtyScope'};

export default function DoctorPage() {
  return (
    <main id="main">
      <PopulationHero />
      <ModelGlance />
      <ProfileExplorer />
      <section className="fs-section" aria-label="Scope and limitations">
        <div className="fs-wrap">
          <div style={{maxWidth: 820}}>
            <Disclosure label="What this demonstrator does not do">
              <ul className="fs-claims" style={{display: 'grid', gridTemplateColumns: '1fr', gap: '.5rem'}}>
                {mobility.limitations.map(l => <li key={l}>{l}.</li>)}
                <li>The fictional profiles are separate from the NHANES model and stand for no real person.</li>
              </ul>
            </Disclosure>
          </div>
        </div>
      </section>
    </main>
  );
}
