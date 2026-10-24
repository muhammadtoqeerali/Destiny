import type {Metadata} from 'next';
import Link from 'next/link';

export const metadata: Metadata = {title: 'Earlier workspaces · FrailtyScope'};

export default function ArchiveIndex() {
  return (
    <main id="main" className="fs-wrap fs-archive">
      <h1 className="fs-h2">Earlier workspaces</h1>
      <p className="fs-muted">Previous versions of the Doctor and Research workspaces, kept for reference. The current product is in the main navigation.</p>
      <div style={{display: 'grid', gap: '.5rem'}}>
        <Link className="fs-link" href="/archive/doctor">Earlier Doctor workspace <span aria-hidden="true">→</span></Link>
        <Link className="fs-link" href="/archive/admin">Earlier Research studio <span aria-hidden="true">→</span></Link>
      </div>
    </main>
  );
}
