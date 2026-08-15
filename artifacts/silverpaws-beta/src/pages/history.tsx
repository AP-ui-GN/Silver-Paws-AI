import { type CSSProperties } from 'react';
import { ArrowLeft, ArrowRight, CalendarDays, CircleAlert, FileVideo, Gauge, Info, Trash2 } from 'lucide-react';
import { Link, useParams } from 'wouter';
import { type Analysis, type Pet } from '@/lib/storage';
import { formatDate, formatDuration, formatRelative } from '@/lib/format';

type Props = { pets: Pet[]; analyses: Analysis[]; deleteAnalysis: (id: string) => void };

function AnalysisList({ analyses, pets }: { analyses: Analysis[]; pets: Pet[] }) {
  if (!analyses.length) {
    return <div className="panel panel-padded text-center py-16"><div className="empty-art mx-auto"><FileVideo size={27} /></div><h2 className="display-title text-3xl mt-5">No walks saved yet.</h2><p className="body-muted text-sm mt-3">Your first local observation will appear here after you run a beta analysis.</p><Link href="/analyze" className="btn-primary mt-6" data-testid="link-history-start-analysis">Record a walk <ArrowRight size={15} /></Link></div>;
  }
  return <div className="panel panel-padded">
    {analyses.map((analysis) => {
      const pet = pets.find((item) => item.id === analysis.petId);
      return <Link href={`/history/${analysis.id}`} className="analysis-row no-underline" key={analysis.id} data-testid={`link-history-analysis-${analysis.id}`}>
        <div className="flex gap-3 items-center min-w-0"><div className="video-icon"><FileVideo size={16} /></div><div className="min-w-0"><div className="font-semibold truncate text-sm">{analysis.fileName}</div><div className="body-muted text-xs mt-1">{pet?.name ?? 'Unknown pet'} · {formatRelative(analysis.createdAt)} · {formatDuration(analysis.durationSeconds)}</div></div></div>
        <div className="flex items-center gap-5"><div className="text-right"><div className="font-bold text-sm">{analysis.strideSymmetryScore ? `${analysis.strideSymmetryScore}/100` : 'Processing'}</div><div className="body-muted text-[10px] mt-1">symmetry</div></div><ArrowRight size={16} className="body-muted" /></div>
      </Link>;
    })}
  </div>;
}

function ResultDetail({ analysis, pet, onDelete }: { analysis: Analysis; pet?: Pet; onDelete: () => void }) {
  const score = analysis.strideSymmetryScore ?? 0;
  return <div className="page-frame max-w-5xl">
    <Link href="/history" className="btn-quiet -ml-3" data-testid="link-back-history"><ArrowLeft size={15} /> All observations</Link>
    <div className="flex flex-wrap items-end justify-between gap-5 mt-6 stagger">
      <div><div className="eyebrow">Saved observation · {formatDate(analysis.createdAt)}</div><h1 className="display-title text-5xl mt-3">A closer look at<br /><span style={{ color: '#b9684d' }}>{pet?.name ?? 'your pet'}’s walk.</span></h1></div>
      <button className="btn-quiet" onClick={() => { if (window.confirm('Remove this saved observation from this device?')) onDelete(); }} data-testid={`button-delete-analysis-${analysis.id}`}><Trash2 size={15} /> Remove</button>
    </div>
    <div className="detail-grid mt-9 stagger-2">
      <div className="panel panel-padded">
        <div className="flex flex-wrap justify-between items-center gap-5">
          <div><div className="eyebrow">Stride symmetry</div><div className="metric-number mt-4">{score}<span className="text-2xl tracking-normal">/100</span></div><p className="body-muted text-sm mt-3">How similar the visible left/right timing appeared in this clip.</p></div>
          <div className="score-ring" style={{ '--score': `${score * 3.6}deg` } as CSSProperties}><div><div className="metric-number text-3xl">{score}</div><div className="mono text-[9px] body-muted mt-1">SCORE</div></div></div>
        </div>
        <div className="grid grid-cols-2 gap-3 mt-9">
          <div className="soft-note p-4"><div className="mono text-[10px] uppercase tracking-wider">Asymmetry</div><div className="font-bold text-2xl mt-2">{analysis.asymmetryPercent ?? '—'}<span className="text-sm">%</span></div></div>
          <div className="soft-note p-4"><div className="mono text-[10px] uppercase tracking-wider">Confidence</div><div className="font-bold text-2xl mt-2">{analysis.confidence ?? '—'}<span className="text-sm">%</span></div></div>
        </div>
      </div>
      <div className="panel panel-padded">
        <div className="flex items-center gap-2"><Gauge size={18} style={{ color: '#b9684d' }} /><div className="eyebrow">What we noticed</div></div>
        <p className="text-lg leading-relaxed mt-5">{analysis.observation}</p>
        <div className="video-meta mt-8"><div className="video-icon"><FileVideo size={16} /></div><div><div className="font-semibold text-sm">{analysis.fileName}</div><div className="body-muted text-xs mt-1">{formatDuration(analysis.durationSeconds)} · {pet?.name ?? 'Pet'}</div></div></div>
      </div>
    </div>
    <section className="soft-note p-5 mt-5 stagger-3 flex gap-3 items-start"><CircleAlert size={19} style={{ color: '#b9684d', flexShrink: 0 }} /><div><h2 className="font-bold text-sm">Important beta context</h2><p className="body-muted text-sm leading-relaxed mt-2">{analysis.limitations}</p></div></section>
    <p className="body-muted text-[11px] mt-6 flex items-center gap-2"><Info size={13} /> Compare observations over time, and share concerns with a veterinary professional.</p>
  </div>;
}

export default function History({ pets, analyses, deleteAnalysis }: Props) {
  const params = useParams<{ id?: string }>();
  const selected = params.id ? analyses.find((analysis) => analysis.id === params.id) : undefined;
  if (params.id && selected) {
    return <ResultDetail analysis={selected} pet={pets.find((pet) => pet.id === selected.petId)} onDelete={() => deleteAnalysis(selected.id)} />;
  }
  if (params.id && !selected) {
    return <div className="page-frame"><div className="panel panel-padded text-center max-w-lg mx-auto mt-16"><CircleAlert size={28} className="mx-auto" style={{ color: '#b9684d' }} /><h1 className="display-title text-3xl mt-5">That observation moved on.</h1><p className="body-muted mt-3">It may have been removed from local storage.</p><Link href="/history" className="btn-primary mt-6" data-testid="link-return-history">Back to history</Link></div></div>;
  }
  return <div className="page-frame max-w-5xl">
    <div className="flex flex-wrap justify-between items-end gap-5 stagger"><div><div className="eyebrow">Your local notebook</div><h1 className="display-title text-5xl mt-3">History, not<br /><span style={{ color: '#b9684d' }}>a verdict.</span></h1><p className="body-muted mt-4 max-w-md leading-relaxed">A dated trail of observations to help you notice patterns and ask better questions.</p></div><Link href="/analyze" className="btn-primary" data-testid="link-history-new-analysis"><FileVideo size={16} /> New analysis</Link></div>
    <div className="flex items-center gap-2 body-muted text-xs mt-8"><CalendarDays size={14} /> {analyses.length} saved observation{analyses.length === 1 ? '' : 's'} on this device</div>
    <div className="mt-4 stagger-2"><AnalysisList analyses={analyses} pets={pets} /></div>
    <div className="soft-note p-4 mt-5 text-xs leading-relaxed"><Info size={14} className="inline mr-2" /> Results are intentionally cautious. A high or low score is not a medical conclusion.</div>
  </div>;
}