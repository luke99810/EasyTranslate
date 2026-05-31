import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import type { PageContent, TextBlock } from '../../types';
import { useSettingsStore } from '../../stores/settingsStore';

interface ImmersiveReaderProps {
  /** The original PDF file_id — used to fetch the raw PDF for pdf.js rendering */
  pdfFileId: string;
  pages: PageContent[];
}

/** Span-level item returned by pdf.js getTextContent() */
interface PdfTextItem {
  str: string;
  transform: number[];
  width: number;
  height: number;
  dir: string;
  fontName: string;
  hasEOL: boolean;
}

/** Group pdf.js text items into paragraph-like segments by vertical proximity. */
function groupPdfTextItems(items: PdfTextItem[]): PdfTextItem[][] {
  if (!items.length) return [];

  const groups: PdfTextItem[][] = [];
  let current: PdfTextItem[] = [];
  let prevY = 0;

  for (const item of items) {
    if (!item.str.trim()) continue;
    const y = item.transform[5]; // y coordinate

    if (current.length && Math.abs(y - prevY) > 3) {
      // Different line — but stay in same group if gap is small
      groups.push(current);
      current = [];
    }

    current.push(item);
    prevY = y;
  }
  if (current.length) groups.push(current);
  return groups;
}

/** Merge pdf text items into a single string for matching. */
function itemsToText(items: PdfTextItem[]): string {
  return items.map(i => i.str).join(' ').trim();
}

/** Build a fuzzy matching score (0..1) between two strings. */
function fuzzyMatch(a: string, b: string): number {
  if (!a || !b) return 0;
  const aNorm = a.toLowerCase().replace(/\s+/g, ' ');
  const bNorm = b.toLowerCase().replace(/\s+/g, ' ');
  if (aNorm === bNorm) return 1;
  // Check if one contains the other (common when paragraph grouping differs)
  if (aNorm.includes(bNorm) || bNorm.includes(aNorm)) return 0.8;
  // Word overlap
  const aWords = new Set(aNorm.split(' ').filter(Boolean));
  const bWords = new Set(bNorm.split(' ').filter(Boolean));
  let overlap = 0;
  for (const w of aWords) { if (bWords.has(w)) overlap++; }
  return overlap / Math.max(aWords.size, bWords.size);
}

/** A matched segment: pdf.js text group + corresponding translated block. */
interface MatchedSegment {
  /** Bounding box of the original text in PDF coordinates [x0, y0, x1, y1] */
  bbox: [number, number, number, number];
  originalText: string;
  translatedText: string;
  isFormula: boolean;
}

/**
 * ImmersiveReader: renders the PDF as-is via pdf.js and overlays
 * translated text on top, matching by position and fuzzy text comparison.
 */
export const ImmersiveReader: React.FC<ImmersiveReaderProps> = ({ pdfFileId, pages }) => {
  const { fontSize } = useSettingsStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRefs = useRef<Map<number, HTMLCanvasElement>>(new Map());
  const overlayRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const pdfDocRef = useRef<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scale, setScale] = useState(1.5);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const [showTranslation, setShowTranslation] = useState(true);

  /** Build segment matching data: match each translated block to pdf.js text groups */
  const buildSegments = useCallback(async () => {
    if (!pdfDocRef.current) return [];

    const allSegments: MatchedSegment[] = [];

    for (let pageIdx = 0; pageIdx < pages.length; pageIdx++) {
      const page = pages[pageIdx];
      const translatedBlocks = page.translated_blocks;
      if (!translatedBlocks.length) continue;

      try {
        const pdfPage = await pdfDocRef.current.getPage(pageIdx + 1);
        const textContent = await pdfPage.getTextContent();
        const pdfItems: PdfTextItem[] = (textContent.items as PdfTextItem[])
          .filter((item: any) => 'str' in item && 'transform' in item);

        const groups = groupPdfTextItems(pdfItems);

        // For each translated block, find the best matching pdf.js text group
        for (const tBlock of translatedBlocks) {
          if (tBlock.block_type === 'formula') {
            // Use the block's own bbox (from backend) for formula positioning
            allSegments.push({
              bbox: tBlock.bbox,
              originalText: tBlock.text,
              translatedText: '',
              isFormula: true,
            });
            continue;
          }

          let bestGroup: PdfTextItem[] | null = null;
          let bestScore = 0;
          let bestIdx = -1;

          for (let gi = 0; gi < groups.length; gi++) {
            const group = groups[gi];
            const groupText = itemsToText(group);
            const score = fuzzyMatch(groupText, tBlock.text);
            if (score > bestScore) {
              bestScore = score;
              bestGroup = group;
              bestIdx = gi;
            }
          }

          if (bestGroup && bestGroup.length && bestScore > 0.3) {
            // Compute bounding box from the matched group
            const transforms = bestGroup.map(g => g.transform);
            const pageViewport = pdfPage.getViewport({ scale: 1 });

            let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
            for (const t of transforms) {
              const x = t[4];
              const y = t[5];
              const h = t[3] || t[0]; // font size from transform
              minX = Math.min(minX, x);
              minY = Math.min(minY, y - Math.abs(h));
              maxX = Math.max(maxX, x + (bestGroup.find(g => g.transform === t)?.width || 0));
              maxY = Math.max(maxY, y);
            }

            allSegments.push({
              bbox: [
                minX,
                minY,
                maxX,
                maxY,
              ],
              originalText: itemsToText(bestGroup),
              translatedText: tBlock.text,
              isFormula: false,
            });
          } else {
            // Fallback: use backend bbox
            allSegments.push({
              bbox: tBlock.bbox,
              originalText: tBlock.text,
              translatedText: tBlock.text,
              isFormula: false,
            });
          }
        }
      } catch (e) {
        console.error(`Failed to process page ${pageIdx + 1}:`, e);
      }
    }

    return allSegments;
  }, [pages]);

  /** Render all PDF pages + overlay translated text */
  const renderPages = useCallback(async () => {
    const container = containerRef.current;
    if (!pdfDocRef.current || !container) return;

    setLoading(true);
    container.innerHTML = '';

    const segments = await buildSegments();

    for (let i = 1; i <= pdfDocRef.current.numPages; i++) {
      const pdfPage = await pdfDocRef.current.getPage(i);
      const viewport = pdfPage.getViewport({ scale });

      // Create page wrapper
      const pageWrapper = document.createElement('div');
      pageWrapper.style.position = 'relative';
      pageWrapper.style.width = `${viewport.width}px`;
      pageWrapper.style.height = `${viewport.height}px`;
      pageWrapper.style.margin = '16px auto';
      pageWrapper.style.boxShadow = '0 2px 12px rgba(0,0,0,0.15)';

      // Create canvas for PDF rendering
      const canvas = document.createElement('canvas');
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      const ctx = canvas.getContext('2d')!;

      await pdfPage.render({
        canvasContext: ctx,
        viewport: viewport,
      }).promise;

      pageWrapper.appendChild(canvas);

      // Create overlay for translated text
      const overlay = document.createElement('div');
      overlay.style.position = 'absolute';
      overlay.style.top = '0';
      overlay.style.left = '0';
      overlay.style.width = `${viewport.width}px`;
      overlay.style.height = `${viewport.height}px`;
      overlay.style.pointerEvents = 'none';
      overlay.style.overflow = 'hidden';
      overlay.dataset.pageNum = String(i);

      // Add translation segments for this page
      const pageContent = pages.find(p => p.page_number === i);
      if (pageContent && segments.length) {
        // Get segments belonging to this page (by matching order)
        const pageSegments = segments.filter(seg => {
          // Use pageContent translated_blocks count to partition segments
          return true; // We'll handle per-page in the loop below
        });

        // Find segments for this specific page
        const translatedBlocks = pageContent.translated_blocks;
        let segOffset = 0;
        for (let pi = 0; pi < i - 1; pi++) {
          segOffset += (pages[pi]?.translated_blocks.length || 0);
        }
        const pageSegs = segments.slice(segOffset, segOffset + translatedBlocks.length);

        for (const seg of pageSegs) {
          const segDiv = document.createElement('div');
          segDiv.style.position = 'absolute';
          segDiv.style.left = `${seg.bbox[0] * scale}px`;
          segDiv.style.top = `${seg.bbox[1] * scale}px`;
          segDiv.style.maxWidth = `${(seg.bbox[2] - seg.bbox[0]) * scale}px`;
          segDiv.style.backgroundColor = 'rgba(255, 255, 200, 0.45)';
          segDiv.style.color = '#1a1a1a';
          segDiv.style.fontSize = `${Math.max(9, fontSize * 0.62)}px`;
          segDiv.style.lineHeight = '1.5';
          segDiv.style.padding = '1px 3px';
          segDiv.style.borderRadius = '2px';
          segDiv.style.overflow = 'hidden';
          segDiv.style.pointerEvents = 'auto';
          segDiv.style.cursor = 'pointer';
          segDiv.style.transition = 'background-color 0.15s ease';
          segDiv.style.wordBreak = 'break-word';
          segDiv.style.zIndex = '10';

          if (seg.isFormula) {
            // Formula: render original LaTeX
            segDiv.style.backgroundColor = 'transparent';
            segDiv.style.color = 'inherit';
            segDiv.style.fontFamily = 'monospace';
            segDiv.style.fontSize = `${Math.max(8, fontSize * 0.58)}px`;
            segDiv.textContent = seg.originalText;
            segDiv.style.pointerEvents = 'none';
          } else {
            segDiv.textContent = seg.translatedText;
            // Hover effect
            segDiv.addEventListener('mouseenter', () => {
              segDiv.style.backgroundColor = 'rgba(255, 255, 200, 0.85)';
            });
            segDiv.addEventListener('mouseleave', () => {
              segDiv.style.backgroundColor = 'rgba(255, 255, 200, 0.45)';
            });
          }

          overlay.appendChild(segDiv);
        }
      }

      pageWrapper.appendChild(overlay);
      container.appendChild(pageWrapper);
    }

    setLoading(false);
  }, [scale, pages, fontSize, buildSegments]);

  /** Load PDF document */
  useEffect(() => {
    let cancelled = false;

    const loadPdf = async () => {
      try {
        const pdfjsLib = await import('pdfjs-dist');
        pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.9.155/pdf.worker.min.mjs`;

        const pdfUrl = `/api/pdf/${pdfFileId}/serve`;
        const loadingTask = pdfjsLib.getDocument(pdfUrl);
        const pdf = await loadingTask.promise;

        if (cancelled) {
          pdf.destroy();
          return;
        }

        pdfDocRef.current = pdf;
        await renderPages();
      } catch (e: any) {
        if (!cancelled) {
          console.error('Failed to load PDF:', e);
          const msg = e.message || '';
          if (msg.includes('Missing PDF') || msg.includes('404')) {
            setError('PDF 文件不存在或已过期，请重新上传并翻译。');
          } else {
            setError(`PDF 加载失败: ${msg}`);
          }
          setLoading(false);
        }
      }
    };

    loadPdf();

    return () => {
      cancelled = true;
      if (pdfDocRef.current) {
        pdfDocRef.current.destroy();
        pdfDocRef.current = null;
      }
    };
  }, [pdfFileId]); // Only re-load when pdfFileId changes

  /** Re-render when scale or showTranslation changes */
  useEffect(() => {
    if (pdfDocRef.current) {
      renderPages();
    }
  }, [scale, showTranslation, fontSize, renderPages]);

  const handleZoomIn = () => setScale(s => Math.min(s + 0.25, 4));
  const handleZoomOut = () => setScale(s => Math.max(s - 0.25, 0.5));

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-red-600 mb-2">{error}</p>
          <button
            onClick={() => {
              setError(null);
              renderPages();
            }}
            className="text-primary-600 hover:underline"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Zoom controls */}
      <div className="fixed bottom-6 right-6 flex items-center gap-2 bg-white rounded-xl shadow-lg border border-gray-200 px-3 py-2 z-50">
        <button
          onClick={handleZoomOut}
          className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-600 font-bold text-lg"
        >
          −
        </button>
        <span className="text-sm text-gray-600 w-12 text-center">{Math.round(scale * 100)}%</span>
        <button
          onClick={handleZoomIn}
          className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 text-gray-600 font-bold text-lg"
        >
          +
        </button>
        <div className="w-px h-5 bg-gray-300 mx-1" />
        <button
          onClick={() => setShowTranslation(!showTranslation)}
          className={`px-2 py-1 rounded-lg text-xs font-medium transition-colors ${
            showTranslation
              ? 'bg-primary-100 text-primary-700'
              : 'bg-gray-100 text-gray-500'
          }`}
          title={showTranslation ? '隐藏译文' : '显示译文'}
        >
          {showTranslation ? '译文开' : '译文关'}
        </button>
      </div>

      {/* Loading indicator */}
      {loading && (
        <div className="fixed inset-0 bg-white/80 flex items-center justify-center z-40">
          <div className="flex flex-col items-center gap-3">
            <svg className="animate-spin h-10 w-10 text-primary-600" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <p className="text-sm text-gray-600">正在渲染 PDF...</p>
          </div>
        </div>
      )}

      {/* PDF container */}
      <div
        ref={containerRef}
        className="bg-gray-200 min-h-screen"
        style={{
          display: showTranslation ? 'block' : 'block',
        }}
      />
    </div>
  );
};
