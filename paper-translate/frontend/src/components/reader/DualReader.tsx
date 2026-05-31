import React, { useRef, useEffect, useState, useMemo } from 'react';
import { useSettingsStore } from '../../stores/settingsStore';
import type { PageContent, TextBlock } from '../../types';

interface DualReaderProps {
  pages: PageContent[];
}

/** Group consecutive text spans into paragraphs based on vertical gap. */
function groupIntoParagraphs(blocks: TextBlock[]): TextBlock[][] {
  if (!blocks.length) return [];

  const paragraphs: TextBlock[][] = [];
  let current: TextBlock[] = [];

  for (const block of blocks) {
    if (block.block_type === 'formula') {
      // Flush current paragraph, then start a new one with the formula
      if (current.length) {
        paragraphs.push(current);
        current = [];
      }
      paragraphs.push([block]);
      continue;
    }

    if (!block.text.trim()) continue;

    if (current.length) {
      const prev = current[current.length - 1];
      const gap = block.bbox[1] - prev.bbox[3]; // curr_top - prev_bottom
      const prevHeight = prev.bbox[3] - prev.bbox[1];
      const lineSpacing = prevHeight > 0 ? prevHeight * 1.8 : 20;

      if (gap > lineSpacing || gap > 15) {
        paragraphs.push(current);
        current = [];
      }
    }

    current.push(block);
  }

  if (current.length) paragraphs.push(current);
  return paragraphs;
}

/** Merge multiple TextBlocks into one by joining their text with spaces. */
function mergeBlocks(blocks: TextBlock[]): TextBlock {
  return {
    ...blocks[0],
    text: blocks.map(b => b.text).join(' '),
  };
}

export const DualReader: React.FC<DualReaderProps> = ({ pages }) => {
  const { layout, fontSize, lineHeight } = useSettingsStore();
  const originalRef = useRef<HTMLDivElement>(null);
  const translatedRef = useRef<HTMLDivElement>(null);
  const [syncing, setSyncing] = useState(false);

  // Pre-compute paragraph-grouped pages
  const groupedPages = useMemo(() => {
    return pages.map(page => ({
      ...page,
      originalParagraphs: groupIntoParagraphs(page.text_blocks),
      translatedParagraphs: page.translated_blocks, // already paragraph-level after backend fix
    }));
  }, [pages]);

  // Sync scroll between original and translated
  useEffect(() => {
    const original = originalRef.current;
    const translated = translatedRef.current;

    if (!original || !translated || syncing) return;

    const handleScroll = (source: HTMLElement, target: HTMLElement) => {
      if (syncing) return;
      setSyncing(true);
      
      const scrollRatio = source.scrollTop / (source.scrollHeight - source.clientHeight);
      target.scrollTop = scrollRatio * (target.scrollHeight - target.clientHeight);
      
      setTimeout(() => setSyncing(false), 50);
    };

    const onOriginalScroll = () => handleScroll(original, translated);
    const onTranslatedScroll = () => handleScroll(translated, original);

    original.addEventListener('scroll', onOriginalScroll);
    translated.addEventListener('scroll', onTranslatedScroll);

    return () => {
      original.removeEventListener('scroll', onOriginalScroll);
      translated.removeEventListener('scroll', onTranslatedScroll);
    };
  }, [syncing]);

  const renderBlock = (block: { text: string; block_type: string }, index: number) => {
    const isFormula = block.block_type === 'formula';
    
    return (
      <span
        key={index}
        className={isFormula ? 'formula mx-1' : ''}
        style={{
          fontSize: isFormula ? '0.9em' : 'inherit',
        }}
      >
        {block.text}
      </span>
    );
  };

  const renderParagraph = (blocks: TextBlock[], idx: number) => {
    const merged = blocks.length > 1 ? mergeBlocks(blocks) : blocks[0];
    const isFormula = merged.block_type === 'formula';

    return (
      <p key={idx} className="reader-text mb-4">
        {isFormula ? (
          <span className="formula mx-1" style={{ fontSize: '0.9em' }}>{merged.text}</span>
        ) : (
          merged.text
        )}
      </p>
    );
  };

  const containerClass = layout === 'horizontal' 
    ? 'flex space-x-4' 
    : 'flex flex-col space-y-4';

  const panelClass = layout === 'horizontal'
    ? 'flex-1 h-[calc(100vh-200px)]'
    : 'h-[calc(50vh-100px)]';

  return (
    <div className={containerClass}>
      {/* Original Panel */}
      <div className={`${panelClass} card overflow-hidden flex flex-col`}>
        <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
          <h3 className="text-sm font-medium text-gray-700">原文</h3>
        </div>
        <div
          ref={originalRef}
          className="flex-1 overflow-y-auto p-6 reader-text"
          style={{
            '--reader-font-size': `${fontSize}px`,
            '--reader-line-height': lineHeight,
          } as React.CSSProperties}
        >
          {groupedPages.map((page) => (
            <div key={page.page_number} className="mb-8">
              <div className="text-xs text-gray-400 mb-2">第 {page.page_number} 页</div>
              {page.originalParagraphs.map((para, idx) => renderParagraph(para, idx))}
            </div>
          ))}
        </div>
      </div>

      {/* Translated Panel */}
      <div className={`${panelClass} card overflow-hidden flex flex-col`}>
        <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
          <h3 className="text-sm font-medium text-gray-700">译文</h3>
        </div>
        <div
          ref={translatedRef}
          className="flex-1 overflow-y-auto p-6 reader-text"
          style={{
            '--reader-font-size': `${fontSize}px`,
            '--reader-line-height': lineHeight,
          } as React.CSSProperties}
        >
          {groupedPages.map((page) => (
            <div key={page.page_number} className="mb-8">
              <div className="text-xs text-gray-400 mb-2">第 {page.page_number} 页</div>
              {page.translatedParagraphs.length > 0 ? (
                page.translatedParagraphs.map((block, idx) => renderParagraph([block], idx))
              ) : (
                <p className="text-gray-400 italic">等待翻译...</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
