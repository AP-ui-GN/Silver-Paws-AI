import { Activity, ClipboardList, PawPrint, Plus, UserRound } from 'lucide-react';
import { type ReactNode } from 'react';
import { Link, useLocation } from 'wouter';

const items = [
  { href: '/', label: 'Overview', icon: Activity },
  { href: '/analyze', label: 'New analysis', icon: Plus },
  { href: '/history', label: 'History', icon: ClipboardList },
  { href: '/pet', label: 'Pet profile', icon: UserRound },
];

function NavItems({ mobile = false }: { mobile?: boolean }) {
  const [location] = useLocation();
  return (
    <nav className={mobile ? 'mobile-bottom-nav' : 'flex flex-col gap-2 mt-14'}>
      {items.map(({ href, label, icon: Icon }) => {
        const active = href === '/' ? location === '/' : location.startsWith(href);
        return (
          <Link
            href={href}
            key={href}
            className={`nav-link ${active ? 'active' : ''}`}
            data-testid={`link-${label.toLowerCase().replaceAll(' ', '-')}`}
          >
            <Icon size={17} strokeWidth={active ? 2.4 : 1.8} />
            <span>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside className="app-nav">
        <Link href="/" className="flex items-center gap-3 no-underline" data-testid="link-brand">
          <span className="brand-mark"><PawPrint size={21} strokeWidth={2.5} /></span>
          <span>
            <span className="brand-word block">SilverPaws</span>
            <span className="brand-sub block">AI beta lab</span>
          </span>
        </Link>
        <NavItems />
        <div className="mt-auto">
          <div className="rounded-2xl p-4" style={{ background: 'rgba(255,255,255,.08)' }}>
            <div className="eyebrow" style={{ color: '#ef9b7f' }}>Browser beta</div>
            <p className="text-xs leading-relaxed mt-2" style={{ color: 'rgba(248,243,232,.65)' }}>
              Your videos and observations stay on this device while testing.
            </p>
          </div>
          <div className="text-[10px] mt-5" style={{ color: 'rgba(248,243,232,.38)' }}>v0.3 · educational use</div>
        </div>
      </aside>
      <div className="content-wrap">
        <header className="mobile-header">
          <Link href="/" className="flex items-center gap-2" data-testid="link-mobile-brand">
            <span className="brand-mark" style={{ width: 32, height: 32 }}><PawPrint size={17} /></span>
            <span className="brand-word">SilverPaws</span>
          </Link>
          <span className="eyebrow">Beta lab</span>
        </header>
        <main>{children}</main>
        <NavItems mobile />
      </div>
    </div>
  );
}