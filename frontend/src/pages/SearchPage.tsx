import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTextSearch, useImageSearch } from '@/hooks/useSearch';
import { useAOIs } from '@/hooks/useAOIs';
import { GlassPanel } from '@/components/common/GlassPanel';
import { BeforeAfterCompare } from '@/components/common/BeforeAfterCompare';
import { SearchResultCard } from '@/components/common/SearchResultCard';
import { ImageZoomModal } from '@/components/common/ImageZoomModal';
import { SimilarTileGrid } from '@/components/common/SimilarTileGrid';
import { SkeletonCard } from '@/components/common/SkeletonCard';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorCard } from '@/components/common/ErrorCard';
import { formatDate } from '@/lib/utils';
import type { CompareResult, SearchResult } from '@/types/api';
import { api } from '@/lib/api';
import {
  Search,
  UploadCloud,
  FileImage,
  Sliders,
  Sparkles,
  Filter,
  X,
} from 'lucide-react';
import { motion } from 'framer-motion';

const exampleQueries = [
  'newly built structures near a river',
  'cleared or deforested land',
  'newly constructed road',
  'water body expansion',
];

export const SearchPage: React.FC = () => {
  const navigate = useNavigate();
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Tab State
  const [activeTab, setActiveTab] = useState<'text' | 'image'>('text');

  // Query Parameters
  const [query, setQuery] = useState('');
  const [selectedAoi, setSelectedAoi] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [topK, setTopK] = useState<number>(12);

  // Image Upload State
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // AOIs for dropdown filter
  const { data: aois } = useAOIs();

  // Search Mutations
  const textSearch = useTextSearch();
  const imageSearch = useImageSearch();

  // Results State
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [lastExecutedQuery, setLastExecutedQuery] = useState<string>('');
  const [zoomImage, setZoomImage] = useState<string | null>(null);
  const [comparisonResult, setComparisonResult] = useState<SearchResult | null>(null);
  const [isComparisonFullscreen, setIsComparisonFullscreen] = useState(false);
  const [comparisonDifferenceUrl, setComparisonDifferenceUrl] = useState<string | null>(null);
  const [hasHydrated, setHasHydrated] = useState(false);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem('sky-analyst-search-state');
      if (saved) {
        const state = JSON.parse(saved) as {
          activeTab?: 'text' | 'image'; query?: string; selectedAoi?: string; dateFrom?: string;
          dateTo?: string; topK?: number; results?: SearchResult[]; lastExecutedQuery?: string;
        };
        if (state.activeTab) setActiveTab(state.activeTab);
        if (state.query !== undefined) setQuery(state.query);
        if (state.selectedAoi !== undefined) setSelectedAoi(state.selectedAoi);
        if (state.dateFrom !== undefined) setDateFrom(state.dateFrom);
        if (state.dateTo !== undefined) setDateTo(state.dateTo);
        if (state.topK !== undefined) setTopK(state.topK);
        if (state.results) setResults(state.results);
        if (state.lastExecutedQuery !== undefined) setLastExecutedQuery(state.lastExecutedQuery);
      }
    } catch {
      sessionStorage.removeItem('sky-analyst-search-state');
    } finally {
      setHasHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!hasHydrated) return;
    sessionStorage.setItem('sky-analyst-search-state', JSON.stringify({
      activeTab, query, selectedAoi, dateFrom, dateTo, topK, results, lastExecutedQuery,
    }));
  }, [hasHydrated, activeTab, query, selectedAoi, dateFrom, dateTo, topK, results, lastExecutedQuery]);

  // Autofocus search input on mount
  useEffect(() => {
    if (activeTab === 'text') {
      searchInputRef.current?.focus();
    }
  }, [activeTab]);

  // Clean up object URL when file changes
  useEffect(() => {
    if (!uploadedFile) {
      setPreviewUrl(null);
      return;
    }
    let objectUrl: string | null = null;
    let cancelled = false;
    setPreviewError(null);
    const formData = new FormData();
    formData.append('file', uploadedFile);
    api.postFormDataBlob('/preview/image', formData)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setPreviewUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) {
          setPreviewUrl(null);
          setPreviewError('Preview unavailable for this image');
        }
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [uploadedFile]);

  useEffect(() => {
    if (!comparisonResult?.reference_vector_id || !comparisonResult.vector_id) return;
    let active = true;
    api.get<CompareResult>('/tiles/compare', {
      before_vector_id: comparisonResult.reference_vector_id,
      after_vector_id: comparisonResult.vector_id,
    }).then((comparison) => {
      if (active) setComparisonDifferenceUrl(comparison.difference_image_url);
    });
    return () => { active = false; };
  }, [comparisonResult]);

  const handleTextSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLastExecutedQuery(query);
    textSearch.mutate(
      {
        query,
        aoi_id: selectedAoi || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        k: topK,
      },
      {
        onSuccess: (data) => {
          setResults(data);
        },
      }
    );
  };

  const handleImageSubmit = () => {
    if (!uploadedFile) return;

    setLastExecutedQuery(uploadedFile.name);
    imageSearch.mutate(
      {
        file: uploadedFile,
        aoi_id: selectedAoi || undefined,
        k: topK,
      },
      {
        onSuccess: (data) => {
          setResults(data);
        },
      }
    );
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setUploadedFile(e.dataTransfer.files[0]);
    }
  };

  const isLoading = textSearch.isPending || imageSearch.isPending;
  const isError = textSearch.isError || imageSearch.isError;
  const currentError = textSearch.error || imageSearch.error;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">
          Semantic & Visual Intelligence Search
        </h1>
        <p className="text-xs text-text-secondary mt-1 font-mono">
          Query satellite imagery using natural language descriptions or visual reference chips
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-white/[0.08] pb-px">
        <button
          onClick={() => setActiveTab('text')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-mono font-medium rounded-t-xl transition-all ${
            activeTab === 'text'
              ? 'text-aurora-300 bg-white/[0.04] border-t border-x border-white/[0.1] border-b-transparent shadow-glow-cyan/10'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <Search size={14} />
          Text Query Search
        </button>
        <button
          onClick={() => setActiveTab('image')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-mono font-medium rounded-t-xl transition-all ${
            activeTab === 'image'
              ? 'text-aurora-300 bg-white/[0.04] border-t border-x border-white/[0.1] border-b-transparent shadow-glow-cyan/10'
              : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <FileImage size={14} />
          Image Chip Search
        </button>
      </div>

      {/* Search Controls Container */}
      <GlassPanel className="p-6 space-y-6">
        {activeTab === 'text' ? (
          <form onSubmit={handleTextSubmit} className="space-y-4">
            <div className="relative">
              <Search
                size={18}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-aurora-400"
              />
              <input
                ref={searchInputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search satellite imagery semantically… (e.g. 'newly built structures near a river')"
                className="w-full pl-12 pr-28 py-3.5 rounded-xl bg-white/[0.03] border border-white/[0.1] text-sm font-sans text-text-primary placeholder:text-text-muted focus:outline-none focus:border-aurora-400 focus:ring-1 focus:ring-aurora-400 transition-all"
              />
              <button
                type="submit"
                disabled={isLoading || !query.trim()}
                className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2 rounded-lg text-xs font-mono font-medium bg-aurora-500 hover:bg-aurora-400 disabled:opacity-40 text-space-950 transition-all shadow-glow-cyan/20"
              >
                {isLoading ? 'Searching…' : 'Execute Search'}
              </button>
            </div>

            {/* Example Queries */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[11px] font-mono text-text-muted flex items-center gap-1">
                <Sparkles size={12} className="text-aurora-400" />
                Prompt Ideas:
              </span>
              {exampleQueries.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => {
                    setQuery(example);
                    // auto trigger
                    setLastExecutedQuery(example);
                    textSearch.mutate(
                      {
                        query: example,
                        aoi_id: selectedAoi || undefined,
                        date_from: dateFrom || undefined,
                        date_to: dateTo || undefined,
                        k: topK,
                      },
                      { onSuccess: (data) => setResults(data) }
                    );
                  }}
                  className="px-2.5 py-1 rounded-full text-[11px] font-mono bg-white/[0.03] hover:bg-white/[0.07] text-text-secondary hover:text-aurora-300 border border-white/[0.06] transition-colors"
                >
                  "{example}"
                </button>
              ))}
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            {/* Drag and Drop Zone */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="relative p-8 rounded-xl border-2 border-dashed border-white/[0.15] hover:border-aurora-400/50 bg-white/[0.02] hover:bg-white/[0.04] transition-all cursor-pointer flex flex-col items-center justify-center text-center group"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    setUploadedFile(e.target.files[0]);
                  }
                }}
              />

              {previewUrl ? (
                <div className="relative w-32 h-32 rounded-lg overflow-hidden border border-aurora-500/40 shadow-glow-cyan/20 mb-3 bg-space-850">
                  <img src={previewUrl} alt="Target Reference" className="w-full h-full object-cover" />
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setUploadedFile(null);
                      if (fileInputRef.current) fileInputRef.current.value = '';
                    }}
                    className="absolute top-1 right-1 p-1 rounded-full bg-space-950/80 text-rose-400 hover:text-rose-300"
                  >
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-text-muted group-hover:text-aurora-400 group-hover:border-aurora-500/40 transition-colors mb-3">
                  <UploadCloud size={24} />
                </div>
              )}

              {previewError && <p className="text-[10px] font-mono text-amber-300">{previewError}</p>}

              <h4 className="text-sm font-semibold text-text-primary mb-1">
                {uploadedFile ? uploadedFile.name : 'Upload Target Satellite Chip'}
              </h4>
              <p className="text-xs text-text-secondary max-w-sm">
                Drag and drop a 224x224 RGB image patch or click to browse local files. CLIP will extract its 512-dim embedding.
              </p>
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleImageSubmit}
                disabled={isLoading || !uploadedFile}
                className="px-5 py-2.5 rounded-xl text-xs font-mono font-medium bg-aurora-500 hover:bg-aurora-400 disabled:opacity-40 text-space-950 transition-all shadow-glow-cyan/20 flex items-center gap-2"
              >
                <Search size={14} />
                {isLoading ? 'Embedding & Searching…' : 'Find Visual Matches'}
              </button>
            </div>
          </div>
        )}

        {/* Filters Bar: AOI Dropdown, Date Range, K Slider */}
        <div className="pt-4 border-t border-white/[0.06] grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end font-mono text-xs">
          <div>
            <label className="block text-text-muted uppercase text-[10px] mb-1.5 flex items-center gap-1">
              <Filter size={10} />
              AOI Filter
            </label>
            <select
              value={selectedAoi}
              onChange={(e) => setSelectedAoi(e.target.value)}
              className="w-full bg-space-850 border border-white/[0.1] rounded-xl px-3 py-2 text-text-primary focus:outline-none focus:border-aurora-400"
            >
              <option value="">All AOIs (Global Index)</option>
              {aois?.map((aoi) => (
                <option key={aoi.aoi_id} value={aoi.aoi_id}>
                  {aoi.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-text-muted uppercase text-[10px] mb-1.5">
              Start Date
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full bg-space-850 border border-white/[0.1] rounded-xl px-3 py-1.5 text-text-primary focus:outline-none focus:border-aurora-400"
            />
          </div>

          <div>
            <label className="block text-text-muted uppercase text-[10px] mb-1.5">
              End Date
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full bg-space-850 border border-white/[0.1] rounded-xl px-3 py-1.5 text-text-primary focus:outline-none focus:border-aurora-400"
            />
          </div>

          <div>
            <div className="flex items-center justify-between text-[10px] text-text-muted mb-1.5">
              <span className="uppercase flex items-center gap-1">
                <Sliders size={10} /> Top-K Limit
              </span>
              <span className="text-aurora-300 font-bold">{topK}</span>
            </div>
            <input
              type="range"
              min={1}
              max={100}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full accent-aurora-400"
            />
          </div>
        </div>
      </GlassPanel>

      {/* Error state */}
      {isError && (
        <ErrorCard
          title="Search Execution Failed"
          message={currentError?.message || 'Error occurred while querying FAISS vector index.'}
        />
      )}

      {/* Results Header */}
      {results && (
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono uppercase tracking-wider text-text-secondary">
            Matches for "{lastExecutedQuery}" ({results.length} chips retrieved)
          </h3>
          <span className="text-[11px] font-mono text-text-muted">Sorted by Cosine Similarity</span>
        </div>
      )}

      {/* Loading Skeletons */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {Array.from({ length: topK > 8 ? 8 : topK }).map((_, i) => (
            <SkeletonCard key={i} hasThumbnail lines={3} />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && results && results.length === 0 && (
        <EmptyState
          icon={Search}
          title="No Matching Tiles Found"
          description={`Zero satellite chips satisfied the semantic criteria for "${lastExecutedQuery}". Try broadening your prompt or adjusting temporal filters.`}
        />
      )}

      {/* Results Grid */}
      {!isLoading && results && results.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {results.map((result, idx) => (
            <motion.div
              key={result.tile_id + idx}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.04 }}
            >
              <SearchResultCard
                result={result}
                index={idx}
                onSelect={(selected) => { setComparisonResult(selected); setComparisonDifferenceUrl(null); }}
                onAnalyze={(selected) => navigate(`/change/${selected.vector_id}`)}
                onOpenZoom={(src) => setZoomImage(src ?? null)}
              />
            </motion.div>
          ))}
        </div>
      )}

      <ImageZoomModal
        src={zoomImage}
        alt="Search result satellite tile"
        open={Boolean(zoomImage)}
        onClose={() => setZoomImage(null)}
      />

      {comparisonResult && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-space-950/90 p-3 backdrop-blur-sm">
          <div className="mx-auto my-4 w-full max-w-7xl">
            <GlassPanel className="relative p-5 bg-space-900/95">
              <button
                type="button"
                aria-label="Close search comparison"
                onClick={() => setComparisonResult(null)}
                className="absolute right-5 top-5 z-20 flex h-9 w-9 items-center justify-center rounded-full border border-white/[0.12] bg-space-950/80 text-text-secondary transition hover:text-text-primary"
              >
                <X size={16} />
              </button>
              <div className="pr-12">
                <h2 className="text-sm font-mono font-semibold text-text-primary">Search Result Comparison</h2>
                <p className="mt-1 text-xs font-mono text-text-muted">{comparisonResult.tile_id} · {formatDate(comparisonResult.date)}</p>
                <div className="mt-3 flex items-center gap-3">
                  {comparisonResult.analysis_available && comparisonResult.vector_id ? (
                    <button
                      type="button"
                      onClick={() => navigate(`/change/${comparisonResult.vector_id}`)}
                      className="inline-flex items-center gap-1.5 rounded-md border border-aurora-500/30 bg-aurora-500/10 px-2.5 py-1.5 text-[10px] font-mono uppercase text-aurora-300 transition hover:bg-aurora-500/20"
                    >
                      View Analysis
                    </button>
                  ) : (
                    <span className="text-[10px] font-mono uppercase text-text-muted">Temporal analysis unavailable</span>
                  )}
                </div>
              </div>
              <div className="mt-4">
                <BeforeAfterCompare
                  beforeUrl={comparisonResult.reference_thumbnail_url}
                  afterUrl={comparisonResult.thumbnail_url}
                  differenceUrl={comparisonDifferenceUrl}
                  beforeDate={comparisonResult.reference_date ?? undefined}
                  afterDate={comparisonResult.date}
                  defaultMode="slider"
                  onFullscreen={() => setIsComparisonFullscreen(true)}
                />
              </div>
              <div className="mt-6 grid grid-cols-1 xl:grid-cols-2 gap-6">
                <SimilarTileGrid
                  vectorId={comparisonResult.reference_vector_id}
                  label="Similar to Before Tile"
                  onNavigate={(tileId) => { setComparisonResult(null); navigate(`/tiles/${tileId}`); }}
                  onOpenZoom={(src) => setZoomImage(src ?? null)}
                />
                <SimilarTileGrid
                  vectorId={comparisonResult.vector_id}
                  label="Similar to After Tile"
                  onNavigate={(tileId) => { setComparisonResult(null); navigate(`/tiles/${tileId}`); }}
                  onOpenZoom={(src) => setZoomImage(src ?? null)}
                />
              </div>
            </GlassPanel>
          </div>
        </div>
      )}

      {comparisonResult && isComparisonFullscreen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-space-950/95 p-3 backdrop-blur-sm">
          <GlassPanel className="relative h-full w-full max-w-7xl p-5 bg-space-900/95">
            <button
              type="button"
              aria-label="Close fullscreen search comparison"
              onClick={() => setIsComparisonFullscreen(false)}
              className="absolute right-5 top-5 z-20 flex h-9 w-9 items-center justify-center rounded-full border border-white/[0.12] bg-space-950/80 text-text-secondary transition hover:text-text-primary"
            >
              <X size={16} />
            </button>
            <BeforeAfterCompare
              beforeUrl={comparisonResult.reference_thumbnail_url}
              afterUrl={comparisonResult.thumbnail_url}
              differenceUrl={comparisonDifferenceUrl}
              beforeDate={comparisonResult.reference_date ?? undefined}
              afterDate={comparisonResult.date}
              defaultMode="slider"
              fullBleed
              onFullscreen={() => setIsComparisonFullscreen(false)}
            />
          </GlassPanel>
        </div>
      )}
    </div>
  );
};
