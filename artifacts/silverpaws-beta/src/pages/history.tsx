import { type CSSProperties } from 'react';
import { ArrowLeft, ArrowRight, CalendarDays, CircleAlert, Download, FileVideo, Gauge, Info, Ruler, Stethoscope, Trash2 } from 'lucide-react';
import { Link, useParams } from 'wouter';
import { displayScore, type Analysis, type Pet } from '@/lib/storage';
import { SAFETY_DISCLAIMER } from '@/lib/disclaimers';
import { formatDate, formatDuration, formatRelative } from '@/lib/format';
import { downloadAnalysisReport } from '@/lib/report';
import { TrendPanel } from '@/components/trend-panel';

type Props = { pets: Pet[]; analyses: Analysis[]; deleteAnalysis: (id: string) => void };

const FACTOR_LABELS: { key: keyof NonNullable<Analysis['factors']>; label: string; help: string }[] = [
  { key: 'movementConsistency', label: 'Movement consistency', help: 'How steady the amount of movement stayed between frames.' },
  { key: 'symmetry', label: 'Stride symmetry', help: 'How similar the left and right leg movement looked.' },
  { key: 'mobility', label: 'Mobility', help: 'Not scored in this release.' },
  { key: 'activity', label: 'Activity', help: 'Share of the clip that contained visible movement.' },
  { key: 'historicalChange', label: 'Change from baseline', help: 'Not scored in this release.' },
];

const SIGNAL_LABELS: Record<string, string> = {
  good: 'Good signal',
  limited: 'Limited signal',
  unusable: 'No usable signal',
};

const PIPELINE_LABELS: Record<string, string> = {
  movenet: 'Pose landmarks (MoveNet)',
  'opencv-motion': 'Picture motion only',
};

/** Format a measurement for display, keeping "not measured" visibly different from zero. */
function formatMeasure(value: number | null | undefined, suffix = '', digits = 3) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 'Not measured';
  return `${Number(value.toFixed(digits))}${suffix}`;
}

function FactorRow({ label, help, score }: { label: string; help: string; score: number | null | undefined }) {
  const measured = typeof score === 'number';
  return (
    <div className="factor-row" data-testid={`row-factor-${label.toLowerCase().replaceAll(' ', '-')}`}>
      <div className="min-w-0">
        <div className="font-semibold text-sm">{label}</div>
        <div className="body-muted text-xs mt-1">{help}</div>
        {measured && <div className="progress-track mt-2 max-w-[240px]"><div className="progress-fill" style={{ width: `${score}%` }} /></div>}
      </div>
      <div className="text-right">
        {measured
          ? <><div className="font-bold text-lg">{score}</div><div className="body-muted text-[10px] mono">OUT OF 100</div></>
          : <span className="tag">Not scored</span>}
      </div>
    </div>
  );
}

function AnalysisList({ analyses, pets }: { analyses: Analysis[]; pets: Pet[] }) {
  if (!analyses.length) {
    return <div className="panel panel-padded text-center py-16"><div className="empty-art mx-auto"><FileVideo size={27} /></div><h2 className="display-title text-3xl mt-5">No walks saved yet.</h2><p className="body-muted text-sm mt-3">Your first observation will appear here after you run an analysis.</p><Link href="/analyze" className="btn-primary mt-6" data-testid="link-history-start-analysis">Record a walk <ArrowRight size={15} /></Link></div>;
  }
  return <div className="panel panel-padded">
    {analyses.map((analysis) => {
      const pet = pets.find((item) => item.id === analysis.petId);
      const score = displayScore(analysis);
      return <Link href={`/history/${analysis.id}`} className="analysis-row no-underline" key={analysis.id} data-testid={`link-history-analysis-${analysis.id}`}>
        <div className="flex gap-3 items-center min-w-0"><div className="video-icon"><FileVideo size={16} /></div><div className="min-w-0"><div className="font-semibold truncate text-sm">{analysis.fileName}</div><div className="body-muted text-xs mt-1">{pet?.name ?? 'Unknown pet'} · {formatRelative(analysis.createdAt)} · {formatDuration(analysis.durationSeconds)}</div></div></div>
        <div className="flex items-center gap-5"><div className="text-right"><div className="font-bold text-sm">{score === null ? 'Not scored' : `${score}/100`}</div><div className="body-muted text-[10px] mt-1">{analysis.signalQuality ? SIGNAL_LABELS[analysis.signalQuality] ?? analysis.signalQuality : 'overall'}</div></div><ArrowRight size={16} className="body-muted" /></div>
      </Link>;
    })}
  </div>;
}

function ResultDetail({ analysis, pet, onDelete }: { analysis: Analysis; pet?: Pet; onDelete: () => void }) {
  const score = displayScore(analysis);
  const factors = analysis.factors;
  const measurements = analysis.measurements;

  return <div className="page-frame max-w-5xl">
    <Link href="/history" className="btn-quiet -ml-3" data-testid="link-back-history"><ArrowLeft size={15} /> All observations</Link>
    <div className="flex flex-wrap items-end justify-between gap-5 mt-6 stagger">
      <div><div className="eyebrow">Saved observation · {formatDate(analysis.createdAt)}</div><h1 className="display-title text-5xl mt-3">A closer look at<br /><span style={{ color: '#b9684d' }}>{pet?.name ?? 'your pet'}’s walk.</span></h1></div>
       <div className="flex flex-wrap gap-2">
         <button type="button" className="btn-secondary" onClick={() => downloadAnalysisReport(analysis, pet)} data-testid={`button-download-report-${analysis.id}`}><Download size={15} /> Download report</button>
         <button className="btn-quiet" onClick={() => { if (window.confirm('Remove this saved observation from this device?')) onDelete(); }} data-testid={`button-delete-analysis-${analysis.id}`}><Trash2 size={15} /> Remove</button>
       </div>
    </div>

    {analysis.concerningChange && (
      <section className="alert-note p-5 mt-7 flex gap-3 items-start stagger" data-testid="text-vet-recommendation">
        <Stethoscope size={19} style={{ flexShrink: 0 }} />
        <div>
          <h2 className="font-bold text-sm">Worth asking a veterinarian about</h2>
          <p className="text-sm leading-relaxed mt-2">The measured values changed enough to be worth a professional opinion. SilverPaws cannot tell you why they changed, and this is not a diagnosis — a veterinarian can examine what a video cannot show.</p>
        </div>
      </section>
    )}

    <div className="detail-grid mt-7 stagger-2">
      <div className="panel panel-padded">
        <div className="flex flex-wrap justify-between items-center gap-5">
          <div>
            <div className="eyebrow">Overall wellness indicator</div>
            <div className="metric-number mt-4" data-testid="text-overall-score">{score === null ? '—' : score}<span className="text-2xl tracking-normal">/100</span></div>
            <p className="body-muted text-sm mt-3">A blend of the factors below. It describes this clip, not your pet’s health.</p>
          </div>
          {score !== null && <div className="score-ring" style={{ '--score': `${score * 3.6}deg` } as CSSProperties}><div><div className="metric-number text-3xl">{score}</div><div className="mono text-[9px] body-muted mt-1">SCORE</div></div></div>}
        </div>
        <div className="flex flex-wrap gap-2 mt-7">
          {analysis.signalQuality && <span className="tag">{SIGNAL_LABELS[analysis.signalQuality] ?? analysis.signalQuality}</span>}
          {analysis.pipeline && <span className="tag">{PIPELINE_LABELS[analysis.pipeline] ?? analysis.pipeline}</span>}
          {analysis.usedLlm && <span className="tag">Model-written summary</span>}
        </div>
        {analysis.signalNote && <p className="body-muted text-xs leading-relaxed mt-4">{analysis.signalNote}</p>}
      </div>
      <div className="panel panel-padded">
        <div className="flex items-center gap-2"><Gauge size={18} style={{ color: '#b9684d' }} /><div className="eyebrow">What we noticed</div></div>
        <p className="text-base leading-relaxed mt-5" data-testid="text-observation">{analysis.observation ?? 'No interpretation was saved for this observation.'}</p>
        <div className="video-meta mt-7"><div className="video-icon"><FileVideo size={16} /></div><div><div className="font-semibold text-sm">{analysis.fileName}</div><div className="body-muted text-xs mt-1">{formatDuration(analysis.durationSeconds)} · {pet?.name ?? 'Pet'}</div></div></div>
      </div>
    </div>

    {factors && (
      <section className="panel panel-padded mt-5 stagger-3">
        <div className="eyebrow">Where the score came from</div>
        <h2 className="display-title text-2xl mt-2">Factor breakdown</h2>
        <p className="body-muted text-sm mt-2 max-w-2xl">Each factor is measured separately. A factor with no score means this clip did not carry enough signal to measure it — it does not mean zero.</p>
        <div className="mt-5">
          {FACTOR_LABELS.map((factor) => (
            <FactorRow key={factor.key} label={factor.label} help={factor.help} score={factors[factor.key]} />
          ))}
        </div>
        {analysis.weightsUsed && Object.keys(analysis.weightsUsed).length > 0 && (
          <p className="body-muted text-xs mt-5">
            Weights used: {Object.entries(analysis.weightsUsed).map(([name, weight]) => `${name} ${Math.round((weight ?? 0) * 100)}%`).join(' · ')}
          </p>
        )}
      </section>
    )}

    {measurements && (
      <section className="panel panel-padded mt-5 stagger-3">
        <div className="flex items-center gap-2"><Ruler size={17} style={{ color: '#b9684d' }} /><div className="eyebrow">Raw measurements</div></div>
        <p className="body-muted text-sm mt-3 max-w-2xl">The values the pipeline measured, before any interpretation.</p>
        <div className="measure-grid mt-5">
          <div className="soft-note p-3"><div className="mono text-[10px] uppercase tracking-wider">Frames read</div><div className="font-bold text-lg mt-1">{formatMeasure(measurements.frameCount, '', 0)}</div></div>
          <div className="soft-note p-3"><div className="mono text-[10px] uppercase tracking-wider">Measured length</div><div className="font-bold text-lg mt-1">{formatMeasure(measurements.durationSeconds, 's', 2)}</div></div>
          <div className="soft-note p-3"><div className="mono text-[10px] uppercase tracking-wider">Mean frame motion</div><div className="font-bold text-lg mt-1">{formatMeasure(measurements.motionMean, '', 4)}</div></div>
          <div className="soft-note p-3"><div className="mono text-[10px] uppercase tracking-wider">Motion variation</div><div className="font-bold text-lg mt-1">{formatMeasure(measurements.motionStd, '', 4)}</div></div>
          <div className="soft-note p-3"><div className="mono text-[10px] uppercase tracking-wider">Frames with movement</div><div className="font-bold text-lg mt-1">{formatMeasure(measurements.motionCoverage, '', 3)}</div></div>
          <div className="soft-note p-3"><div className="mono text-[10px] uppercase tracking-wider">Stride symmetry</div><div className="font-bold text-lg mt-1">{formatMeasure(measurements.strideSymmetry)}</div></div>
          <div className="soft-note p-3"><div className="mono text-[10px] uppercase tracking-wider">Asymmetry</div><div className="font-bold text-lg mt-1">{formatMeasure(analysis.asymmetryPercent, '%', 2)}</div></div>
          <div className="soft-note p-3"><div className="mono text-[10px] uppercase tracking-wider">Hip stability</div><div className="font-bold text-lg mt-1">{formatMeasure(measurements.hipStability)}</div></div>
          <div className="soft-note p-3"><div className="mono text-[10px] uppercase tracking-wider">Pose confidence</div><div className="font-bold text-lg mt-1">{formatMeasure(analysis.confidence, '%', 1)}</div></div>
        </div>
      </section>
    )}

    <section className="soft-note p-5 mt-5 stagger-3 flex gap-3 items-start"><CircleAlert size={19} style={{ color: '#b9684d', flexShrink: 0 }} /><div><h2 className="font-bold text-sm">Important limitations</h2><p className="body-muted text-sm leading-relaxed mt-2" data-testid="text-limitations">{analysis.limitations ?? SAFETY_DISCLAIMER}</p></div></section>
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
    <TrendPanel analyses={analyses} />
    <div className="mt-4 stagger-2"><AnalysisList analyses={analyses} pets={pets} /></div>
    <div className="soft-note p-4 mt-5 text-xs leading-relaxed"><Info size={14} className="inline mr-2" /> Results are intentionally cautious. A high or low score is not a medical conclusion.</div>
  </div>;
}
