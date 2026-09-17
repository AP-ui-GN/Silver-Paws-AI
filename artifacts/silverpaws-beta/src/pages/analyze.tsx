import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, CircleAlert, FileVideo, Film, LoaderCircle, LockKeyhole, PawPrint, Play, RotateCcw, Sparkles, UploadCloud } from 'lucide-react';
import { Link, useLocation } from 'wouter';
import { findBaseline, toAnalysisRecord, type Analysis, type Pet } from '@/lib/storage';
import { checkClip, describeAnalysisError, requestAnalysis } from '@/lib/analysis-api';
import { formatDuration } from '@/lib/format';

type Props = {
  pets: Pet[];
  analyses: Analysis[];
  addAnalysis: (analysis: Omit<Analysis, 'id' | 'createdAt'>) => Analysis;
};

type Phase = 'upload' | 'review' | 'processing' | 'done';

// Shown in order while the request is in flight. The service does not report
// progress, so these describe the pipeline stages rather than a percentage.
const STAGES = [
  'Sending the clip to the analysis service',
  'Reading frames and measuring movement',
  'Scoring the wellness factors',
  'Writing a plain-language note',
];

export default function Analyze({ pets, analyses, addAnalysis }: Props) {
  const [, setLocation] = useLocation();
  const [petId, setPetId] = useState(pets[0]?.id ?? '');
  const [file, setFile] = useState<File | null>(null);
  const [duration, setDuration] = useState(0);
  const [previewUrl, setPreviewUrl] = useState('');
  const [source, setSource] = useState('');
  const [license, setLicense] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [phase, setPhase] = useState<Phase>('upload');
  const [stage, setStage] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const requestRef = useRef<AbortController | null>(null);

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  // Drop an in-flight request if the user navigates away mid-analysis.
  useEffect(() => () => requestRef.current?.abort(), []);

  useEffect(() => {
    if (phase !== 'processing') return;
    const started = Date.now();
    const timer = window.setInterval(() => {
      const seconds = Math.floor((Date.now() - started) / 1000);
      setElapsed(seconds);
      setStage(Math.min(STAGES.length - 1, Math.floor(seconds / 4)));
    }, 500);
    return () => window.clearInterval(timer);
  }, [phase]);

  const selectFile = (selected: File | undefined) => {
    if (!selected) return;
    setError('');

    const immediateProblem = checkClip(selected, 0);
    if (immediateProblem) {
      setError(immediateProblem.message);
      return;
    }

    const url = URL.createObjectURL(selected);
    setFile(selected);
    setPreviewUrl(url);
    setPhase('review');
    setDuration(0);

    // Duration is read for display and for the length check. A container the
    // browser cannot measure is still accepted, because the pipeline measures it.
    const video = document.createElement('video');
    video.preload = 'metadata';
    video.onloadedmetadata = () => {
      const seconds = Number.isFinite(video.duration) ? Math.round(video.duration) : 0;
      setDuration(seconds);
      const durationProblem = checkClip(selected, seconds);
      if (durationProblem) setError(durationProblem.message);
    };
    video.onerror = () => setDuration(0);
    video.src = url;
  };

  const reset = () => {
    requestRef.current?.abort();
    setFile(null);
    setDuration(0);
    setPreviewUrl('');
    setSource('');
    setLicense('');
    setSourceUrl('');
    setStage(0);
    setElapsed(0);
    setPhase('upload');
    setError('');
    if (inputRef.current) inputRef.current.value = '';
  };

  const runAnalysis = async () => {
    if (!file) return;

    const problem = checkClip(file, duration);
    if (problem) {
      setError(problem.message);
      return;
    }

    const controller = new AbortController();
    requestRef.current = controller;
    setError('');
    setStage(0);
    setElapsed(0);
    setPhase('processing');

    const pet = pets.find((item) => item.id === petId);
    const baseline = findBaseline(analyses, petId);

    try {
      const result = await requestAnalysis({
        file,
        petName: pet?.name,
        previousOverall: baseline?.overallScore,
        previousPipeline: baseline?.pipeline,
        signal: controller.signal,
      });

      const saved = addAnalysis(
        toAnalysisRecord(result, {
          petId,
          fileName: file.name,
          durationSeconds: duration,
          source,
          license,
          sourceUrl,
        }),
      );

      setPhase('done');
      window.setTimeout(() => setLocation(`/history/${saved.id}`), 400);
    } catch (caught) {
      if (controller.signal.aborted) return;
      setError(describeAnalysisError(caught));
      setPhase('review');
    } finally {
      requestRef.current = null;
    }
  };

  const currentPet = pets.find((pet) => pet.id === petId);

  return (
    <div className="page-frame max-w-4xl">
      <Link href="/" className="btn-quiet -ml-3" data-testid="link-back-home"><ArrowLeft size={15} /> Overview</Link>
      <div className="mt-6 stagger">
        <div className="eyebrow">New mobility observation</div>
        <h1 className="display-title text-5xl mt-3">One walk.<br /><span style={{ color: '#b9684d' }}>A little more context.</span></h1>
        <p className="body-muted mt-4 max-w-lg leading-relaxed">Choose a short video and the analysis service will measure the movement it can see, then save an educational observation.</p>
      </div>

      <div className="flex items-center gap-2 mt-9 text-xs font-semibold">
        {['Choose video', 'Review clip', 'Analysis'].map((label, index) => {
          const active = index === 0 ? phase === 'upload' : index === 1 ? phase === 'review' : phase === 'processing' || phase === 'done';
          const complete = (index === 0 && phase !== 'upload') || (index === 1 && (phase === 'processing' || phase === 'done'));
          return <div key={label} className="flex items-center gap-2"><span className="w-7 h-7 rounded-full grid place-items-center" style={{ background: active || complete ? '#174946' : '#e3e9df', color: active || complete ? '#f8f3e8' : '#668078' }}>{complete ? <Check size={14} /> : index + 1}</span><span className={active ? '' : 'body-muted'}>{label}</span>{index < 2 && <span className="w-8 h-px bg-border mx-1" />}</div>;
        })}
      </div>

      {phase === 'upload' && (
        <section className="panel panel-padded mt-7 stagger-2">
          <div className="grid md:grid-cols-[1fr_220px] gap-7">
            <div>
              <label className="field-label" htmlFor="pet-select">Who is in this video?</label>
              {pets.length
                ? <select id="pet-select" className="field-input" value={petId} onChange={(event) => setPetId(event.target.value)} data-testid="select-analysis-pet">{pets.map((pet) => <option value={pet.id} key={pet.id}>{pet.name} · {pet.species}</option>)}</select>
                : <div className="soft-note p-3 text-sm" data-testid="text-no-pet-warning">Create a pet profile before starting an analysis. <Link href="/pet" className="font-bold underline">Add a pet</Link></div>}
              <div className="dotted-drop mt-6 min-h-[245px] flex flex-col items-center justify-center text-center p-7">
                <div className="empty-art"><UploadCloud size={27} /></div>
                <h2 className="font-bold text-lg mt-5">Drop a walking video here</h2>
                <p className="body-muted text-sm mt-2">Side view, steady camera, 5–60 seconds</p>
                <button type="button" className="btn-secondary mt-5" onClick={() => inputRef.current?.click()} disabled={!pets.length} data-testid="button-choose-video"><Film size={16} /> Choose video</button>
                <input ref={inputRef} className="hidden" type="file" accept="video/*" onChange={(event) => selectFile(event.target.files?.[0])} data-testid="input-walking-video" />
              </div>
              {error && <div className="text-sm mt-3 flex items-center gap-2" style={{ color: '#a54339' }} role="alert" data-testid="text-upload-error"><CircleAlert size={15} />{error}</div>}
            </div>
            <div className="soft-note p-4 h-fit">
              <LockKeyhole size={17} />
              <h3 className="font-bold text-sm mt-3">Sent only for analysis</h3>
              <p className="body-muted text-xs leading-relaxed mt-2">The clip is sent to the SilverPaws analysis service, measured in a temporary folder, and deleted straight after. Only the numbers and the note are saved, in this browser.</p>
            </div>
          </div>
        </section>
      )}

      {phase === 'review' && file && (
        <section className="panel panel-padded mt-7 stagger-2">
          <div className="flex justify-between items-start gap-4"><div><div className="eyebrow">Step two · check your clip</div><h2 className="display-title text-3xl mt-2">Looks ready to read.</h2></div><button className="btn-quiet" onClick={reset} data-testid="button-replace-video"><RotateCcw size={15} /> Replace</button></div>
          <div className="grid md:grid-cols-[1.1fr_.9fr] gap-7 mt-7">
            <div className="rounded-2xl overflow-hidden aspect-video bg-[#dbe7d7] flex items-center justify-center relative">
              {previewUrl ? <video src={previewUrl} controls className="w-full h-full object-contain" data-testid="video-preview" /> : <FileVideo size={42} style={{ color: '#5d8177' }} />}
              {!previewUrl && <div className="absolute inset-0 grid place-items-center"><Play size={25} /></div>}
            </div>
            <div>
              <div className="video-meta"><div className="video-icon"><FileVideo size={16} /></div><div className="min-w-0"><div className="font-semibold text-sm truncate">{file.name}</div><div className="body-muted text-xs mt-1">{duration ? formatDuration(duration) : 'Duration will be measured'} · {Math.round(file.size / 1024)} KB</div></div></div>
              <div className="mt-6"><label className="field-label" htmlFor="pet-select-review">Pet</label><select id="pet-select-review" className="field-input" value={petId} onChange={(event) => setPetId(event.target.value)} data-testid="select-review-pet">{pets.map((pet) => <option value={pet.id} key={pet.id}>{pet.name}</option>)}</select></div>
               <div className="soft-note p-4 mt-6">
                 <div className="eyebrow">Optional sharing context</div>
                 <p className="body-muted text-xs leading-relaxed mt-2">Add attribution details if this clip came from a shared library or another source. Leave these blank for a private local video.</p>
                 <div className="mt-4">
                   <label className="field-label" htmlFor="analysis-source">Source</label>
                   <input id="analysis-source" className="field-input" value={source} onChange={(event) => setSource(event.target.value)} placeholder="e.g. Personal video or test library" data-testid="input-analysis-source" />
                 </div>
                 <div className="mt-4">
                   <label className="field-label" htmlFor="analysis-license">License</label>
                   <input id="analysis-license" className="field-input" value={license} onChange={(event) => setLicense(event.target.value)} placeholder="e.g. CC BY 4.0 or permission granted" data-testid="input-analysis-license" />
                 </div>
                 <div className="mt-4">
                   <label className="field-label" htmlFor="analysis-source-url">Source link</label>
                   <input id="analysis-source-url" type="url" className="field-input" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="https://..." data-testid="input-analysis-source-url" />
                 </div>
               </div>
              {error && <div className="text-sm mt-4 flex items-start gap-2" style={{ color: '#a54339' }} role="alert" data-testid="text-analysis-error"><CircleAlert size={15} className="mt-[2px] shrink-0" />{error}</div>}
              <button className="btn-primary w-full mt-6" onClick={runAnalysis} disabled={!petId} data-testid="button-run-analysis"><Sparkles size={16} style={{ color: '#ef9b7f' }} /> Run analysis <ArrowRight size={15} /></button>
              <p className="body-muted text-[11px] leading-relaxed mt-4">The result describes visible movement only. It is not a diagnosis and should never replace veterinary advice.</p>
            </div>
          </div>
        </section>
      )}

      {phase === 'processing' && (
        <section className="panel panel-padded mt-7 stagger-2 text-center max-w-2xl mx-auto" aria-busy="true">
          <div className="empty-art mx-auto" style={{ animation: 'pulse-soft 1.3s infinite' }}><LoaderCircle size={28} className="animate-spin" /></div>
          <div className="eyebrow mt-7">Analysis in progress</div>
          <h2 className="display-title text-3xl mt-2" data-testid="text-processing-stage">{STAGES[stage]}</h2>
          <p className="body-muted text-sm mt-3">Keeping the language clear, cautious, and useful.</p>
          <div className="progress-track progress-indeterminate mt-8" role="progressbar" aria-label="Analyzing clip" />
          <div className="mono text-xs body-muted mt-3">{elapsed}s elapsed · a longer clip takes longer to measure</div>
        </section>
      )}

      {phase === 'done' && (
        <section className="panel panel-padded mt-7 text-center"><div className="empty-art mx-auto"><Check size={29} /></div><h2 className="display-title text-3xl mt-5">Your note is ready.</h2><p className="body-muted text-sm mt-2">Opening the saved observation for {currentPet?.name ?? 'your pet'}…</p></section>
      )}
      {phase === 'review' && <div className="flex items-center gap-2 body-muted text-xs mt-6"><PawPrint size={14} /> You’re in control — review the clip before anything runs.</div>}
    </div>
  );
}
