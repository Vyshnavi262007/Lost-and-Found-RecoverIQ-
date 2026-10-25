import { useEffect, useMemo, useRef } from 'react';
import { ImagePlus, X } from 'lucide-react';

export const MAX_FILES = 5;
export const MAX_MB = 5;
const OK_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

/** Controlled multi-photo picker with previews and client-side type/size checks. */
export default function ImagePicker({ files, onChange, onProblem, existing = [], onRemoveExisting }) {
  const input = useRef(null);
  const previews = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files]);
  useEffect(() => () => previews.forEach(URL.revokeObjectURL), [previews]);

  const add = (list) => {
    const next = [...files];
    for (const f of Array.from(list)) {
      if (!OK_TYPES.includes(f.type)) { onProblem?.(`${f.name}: only JPEG, PNG or WebP images are allowed.`); continue; }
      if (f.size > MAX_MB * 1024 * 1024) { onProblem?.(`${f.name} is larger than ${MAX_MB} MB.`); continue; }
      if (next.length + existing.length >= MAX_FILES) { onProblem?.(`You can add at most ${MAX_FILES} photos.`); break; }
      next.push(f);
    }
    onChange(next);
    if (input.current) input.current.value = '';
  };

  return (
    <div>
      <div className="flex flex-wrap gap-3">
        {existing.map((img) => (
          <div key={img.id} className="relative h-24 w-24 overflow-hidden rounded-lg border border-slate-200">
            <img src={img.url} alt="Saved item" className="h-full w-full object-cover" />
            <button type="button" onClick={() => onRemoveExisting(img.id)} aria-label="Remove photo" className="absolute right-1 top-1 rounded-full bg-white/90 p-0.5 shadow"><X className="h-3.5 w-3.5" /></button>
          </div>
        ))}
        {previews.map((src, i) => (
          <div key={src} className="relative h-24 w-24 overflow-hidden rounded-lg border border-slate-200">
            <img src={src} alt={`Selected ${i + 1}`} className="h-full w-full object-cover" />
            <button type="button" onClick={() => onChange(files.filter((_, j) => j !== i))} aria-label="Remove photo" className="absolute right-1 top-1 rounded-full bg-white/90 p-0.5 shadow"><X className="h-3.5 w-3.5" /></button>
          </div>
        ))}
        {files.length + existing.length < MAX_FILES && (
          <button type="button" onClick={() => input.current?.click()} className="flex h-24 w-24 flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-slate-300 text-xs text-slate-500 hover:border-navy-400 hover:text-navy-700">
            <ImagePlus className="h-5 w-5" /> Add photo
          </button>
        )}
      </div>
      <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={(e) => add(e.target.files)} />
      <p className="mt-2 text-xs text-slate-500">Up to {MAX_FILES} photos, JPEG/PNG/WebP, {MAX_MB} MB each.</p>
    </div>
  );
}
