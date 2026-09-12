import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, CircleAlert, FileVideo, Film, LoaderCircle, LockKeyhole, PawPrint, Play, RotateCcw, Sparkles, UploadCloud } from 'lucide-react';
import { Link, useLocation } from 'wouter';
import { type Analysis, type Pet } from '@/lib/storage';
import { formatDuration } from '@/lib/format';

type Props = { pets: Pet[]; addAnalysis: (analysis: Omit<Analysis, 'id' | 'createdAt'>) => Analysis };

export default function Analyze({ pets, addAnalysis }: Props) {
  const [, setLocation] = useLocation();
  const [petId, setPetId] = useState(pets[0]?.id ?? '');
  const [file, setFile] = useState<File | null>(null);
  const [duration, setDuration] = useState(0);
  const [previewUrl, setPreviewUrl] = useState('');
  const [source, setSource] = useState('');
  const [license, setLicense] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [phase, setPhase] = useState<'upload' | 'review' | 'processing' | 'done'>('upload');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  useEffect(() => {
    if (phase !== 'processing') return;
    const steps = [
      [22, 'Reading the walking clip'],
      [46, 'Mapping visible steps'],
      [71, 'Comparing left and right timing'],
      [92, 'Preparing a plain-language note'],
    ] as const;
    let index = 0;
    const timer = window.setInterval(() => {
      setProgress(steps[index][0]);
      index += 1;
      if (index >= steps.length) window.clearInterval(timer);
    }, 700);
    const finish = window.setTimeout(() => {
      const result = addAnalysis({
        petId,
        fileName: file?.name ?? 'walking-clip.mp4',
        durationSeconds: duration || 12,
        status: 'complete',
        strideSymmetryScore: 74 + Math.floor(Math.random() * 19),
        asymmetryPercent: 5 + Math.floor(Math.random() * 8),
        confidence: 70 + Math.floor(Math.random() * 18),
        observation: 'The visible stride looked mostly even across this clip, with a mild timing difference that is worth watching across more walks.',
        limitations: 'This is a simulated beta observation from one short clip. It is not a diagnosis and cannot rule out pain or injury.',
        source: source.trim() || undefined,
        license: license.trim() || undefined,
        sourceUrl: sourceUrl.trim() || undefined,
      });
      setProgress(100);
      setPhase('done');
      window.setTimeout(() => setLocation(`/history/${result.id}`), 500);
    }, 3400);
    return () => { window.clearInterval(timer); window.clearTimeout(finish); };
  }, [addAnalysis, duration, file, license, petId, phase, setLocation, source, sourceUrl]);

  const selectFile = (selected: File | undefined) => {
    if (!selected) return;
    setError('');
    if (!selected.type.startsWith('video/')) {
      setError('Please choose a video file. MP4, MOV, and WebM work well for this beta.');
      return;
    }
    const url = URL.createObjectURL(selected);
    setFile(selected);
    setPreviewUrl(url);
    setPhase('review');
    const video = document.createElement('video');
    video.preload = 'metadata';
    video.onloadedmetadata = () => setDuration(Number.isFinite(video.duration) ? Math.round(video.duration) : 0);
    video.src = url;
  };

  const reset = () => {
    setFile(null);
    setDuration(0);
    setPreviewUrl('');
    setSource('');
    setLicense('');
    setSourceUrl('');
    setProgress(0);
    setPhase('upload');
    setError('');
    if (inputRef.current) inputRef.current.value = '';
  };

  const currentPet = pets.find((pet) => pet.id === petId);
  const processingMessage = progress < 40 ? 'Reading the walking clip' : progress < 65 ? 'Mapping visible steps' : progress < 90 ? 'Comparing left and right timing' : 'Preparing a plain-language note';

  return (
    <div className="page-frame max-w-4xl">
      <Link href="/" className="btn-quiet -ml-3" data-testid="link-back-home"><ArrowLeft size={15} /> Overview</Link>
      <div className="mt-6 stagger">
        <div className="eyebrow">New mobility observation</div>
        <h1 className="display-title text-5xl mt-3">One walk.<br /><span style={{ color: '#b9684d' }}>A little more context.</span></h1>
        <p className="body-muted mt-4 max-w-lg leading-relaxed">Choose a short video and we’ll create a simulated, educational observation in your browser.</p>
      </div>

      <div className="flex items-center gap-2 mt-9 text-xs font-semibold">
        {['Choose video', 'Review clip', 'Beta analysis'].map((label, index) => {
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
              {pets.length ? <select id="pet-select" className="field-input" value={petId} onChange={(event) => setPetId(event.target.value)} data-testid="select-analysis-pet">{pets.map((pet) => <option value={pet.id} key={pet.id}>{pet.name} · {pet.species}</option>)}</select> : <div className="soft-note p-3 text-sm">Create a pet profile before starting an analysis.</div>}
              <div className="dotted-drop mt-6 min-h-[245px] flex flex-col items-center justify-center text-center p-7">
                <div className="empty-art"><UploadCloud size={27} /></div>
                <h2 className="font-bold text-lg mt-5">Drop a walking video here</h2>
                <p className="body-muted text-sm mt-2">Side view, steady camera, 5–60 seconds</p>
                <button type="button" className="btn-secondary mt-5" onClick={() => inputRef.current?.click()} disabled={!pets.length} data-testid="button-choose-video"><Film size={16} /> Choose video</button>
                <input ref={inputRef} className="hidden" type="file" accept="video/*" onChange={(event) => selectFile(event.target.files?.[0])} data-testid="input-walking-video" />
              </div>
              {error && <div className="text-sm mt-3 flex items-center gap-2" style={{ color: '#a54339' }}><CircleAlert size={15} />{error}</div>}
            </div>
            <div className="soft-note p-4 h-fit">
              <LockKeyhole size={17} />
              <h3 className="font-bold text-sm mt-3">Private by default</h3>
              <p className="body-muted text-xs leading-relaxed mt-2">The selected file is used only in this tab. This beta does not upload it to a server.</p>
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
              <div className="video-meta"><div className="video-icon"><FileVideo size={16} /></div><div className="min-w-0"><div className="font-semibold text-sm truncate">{file.name}</div><div className="body-muted text-xs mt-1">{duration ? formatDuration(duration) : 'Duration will be estimated'} · {Math.round(file.size / 1024)} KB</div></div></div>
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
              <button className="btn-primary w-full mt-6" onClick={() => { setProgress(5); setPhase('processing'); }} data-testid="button-run-analysis"><Sparkles size={16} style={{ color: '#ef9b7f' }} /> Run beta analysis <ArrowRight size={15} /></button>
              <p className="body-muted text-[11px] leading-relaxed mt-4">The result is simulated for this beta. It describes visible movement only and should never replace veterinary advice.</p>
            </div>
          </div>
        </section>
      )}

      {phase === 'processing' && (
        <section className="panel panel-padded mt-7 stagger-2 text-center max-w-2xl mx-auto">
          <div className="empty-art mx-auto" style={{ animation: 'pulse-soft 1.3s infinite' }}><LoaderCircle size={28} className="animate-spin" /></div>
          <div className="eyebrow mt-7">Simulated analysis in progress</div>
          <h2 className="display-title text-3xl mt-2">{processingMessage}</h2>
          <p className="body-muted text-sm mt-3">Keeping the language clear, cautious, and useful.</p>
          <div className="progress-track mt-8"><div className="progress-fill" style={{ width: `${progress}%` }} /></div>
          <div className="mono text-xs body-muted mt-3">{progress}% · local browser simulation</div>
        </section>
      )}

      {phase === 'done' && (
        <section className="panel panel-padded mt-7 text-center"><div className="empty-art mx-auto"><Check size={29} /></div><h2 className="display-title text-3xl mt-5">Your note is ready.</h2><p className="body-muted text-sm mt-2">Opening the saved observation for {currentPet?.name ?? 'your pet'}…</p></section>
      )}
      {phase !== 'upload' && phase !== 'processing' && phase !== 'done' && <div className="flex items-center gap-2 body-muted text-xs mt-6"><PawPrint size={14} /> You’re in control — review the clip before anything runs.</div>}
    </div>
  );
}