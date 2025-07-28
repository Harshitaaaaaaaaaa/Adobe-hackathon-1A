import fitz
import json
import re
import argparse
import numpy as np
from pathlib import Path
from collections import Counter
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple, Optional

class Config:
    TITLE_MIN_CHARS = 10
    SIMILARITY_THRESHOLD = 0.85
    ALPHA_CHAR_RATIO_THRESHOLD = 0.4
    HEADING_MIN_CHARS = 3
    LANG_CONFIG_FILE = "languages.json"
    W_FONT_SIZE = 25
    W_VERTICAL_GAP = 40
    W_IS_BOLD = 15
    W_TEXT_LENGTH = 20

def load_language_config() -> Dict[str, Any]:
    try:
        with open(Config.LANG_CONFIG_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
        for lang, settings in data.items():
            if 'numbered_heading_regex' in settings:
                settings['numbered_heading_regex'] = re.compile(settings['numbered_heading_regex'])
        return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Error with '{Config.LANG_CONFIG_FILE}': {e}"); return {}

def format_embedded_toc(toc: List[Tuple[int, str, int]]) -> List[Dict[str, Any]]:
    return [{"level": f"H{level}", "text": title.strip(), "page": page} for level, title, page in toc]

def identify_repeated_elements(blocks: List[Dict[str, Any]], min_pages: int = 3) -> set:
    text_positions = {}
    for b in blocks:
        key = (b['text'].strip(), round(b['bbox'][1] / 10))
        if key not in text_positions: text_positions[key] = set()
        text_positions[key].add(b['page'])
    return {key for key, pages in text_positions.items() if len(pages) >= min_pages}

def extract_text_blocks(doc: fitz.Document) -> List[Dict[str, Any]]:
    blocks = []
    for page_num, page in enumerate(doc, start=1):
        for block in page.get_text("dict")["blocks"]:
            if "lines" not in block: continue
            for line in block["lines"]:
                if not line["spans"]: continue
                main_span = max(line["spans"], key=lambda s: s["size"])
                text = " ".join([s["text"] for s in line["spans"]]).strip()
                if not text: continue
                blocks.append({
                    "text": text, "font_size": main_span["size"], "bold": bool(main_span["flags"] & 2**1),
                    "page": page_num, "bbox": line["bbox"]
                })
    blocks.sort(key=lambda b: (b['page'], b['bbox'][1]))
    return blocks

def normalize_text(text: str) -> str:
    if not text: return ""
    return "".join([c for i, c in enumerate(text) if i == 0 or c != text[i-1] or not c.isalnum()])

def detect_title(doc: fitz.Document, blocks: List[Dict[str, Any]]) -> str:
    if not doc.page_count > 0: return ""
    page_width, page_height = doc[0].rect.width, doc[0].rect.height
    candidates = []
    for b in blocks:
        if b['page'] != 1 or len(b['text']) < Config.TITLE_MIN_CHARS: continue
        score = b['font_size']
        if b['bbox'][1] < page_height * 0.4: score *= 1.5
        center_pos = (b['bbox'][0] + b['bbox'][2]) / 2
        center_diff = abs(center_pos - page_width / 2)
        score *= max(0.1, 1 - (center_diff / (page_width / 2)))
        candidates.append({'score': score, 'text': b['text']})
    if not candidates: return ""
    return normalize_text(max(candidates, key=lambda c: c['score'])['text'])

def is_similar(a: str, b: str) -> bool:
    """Checks if two strings are similar based on a threshold."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= Config.SIMILARITY_THRESHOLD

def cluster_font_sizes(blocks: List[Dict[str, Any]]) -> Tuple[float, float]:
    font_sizes = [b['font_size'] for b in blocks if b['font_size'] > 0]
    if not font_sizes: return 0, 0
    freq = Counter(round(size) for size in font_sizes)
    body_size = freq.most_common(1)[0][0]
    
    heading_sizes = [size for size in freq if size > body_size]
    primary_heading_size = max(heading_sizes) if heading_sizes else body_size
    return body_size, primary_heading_size

def classify_headings(blocks: List[Dict[str, Any]], title: str, lang_settings: Dict) -> List[Dict[str, Any]]:
    """Classifies headings using a weighted scoring system and adaptive thresholds."""
    body_size, primary_heading_size = cluster_font_sizes(blocks)
    if body_size == 0 or primary_heading_size <= body_size: return []

    numbered_heading_regex = lang_settings.get('numbered_heading_regex')
    repeated_elements = identify_repeated_elements(blocks)
    
    scored_candidates = []
    last_y1 = 0
    last_page = 0

    # Phase 1: Score all potential heading candidates
    for i, b in enumerate(blocks):
        text, size, bbox = b['text'], b['font_size'], b['bbox']
        
        # Basic filtering
        if size <= body_size or not text or is_similar(text, title):
            last_y1 = bbox[3] if i > 0 else 0; last_page = b['page']; continue
        if (text.strip(), round(bbox[1] / 10)) in repeated_elements:
            last_y1 = bbox[3]; last_page = b['page']; continue

        score = 0
        # Score for font size (normalized against body text)
        if primary_heading_size > body_size:
            score += (size - body_size) / (primary_heading_size - body_size) * Config.W_FONT_SIZE

        # Score for vertical gap
        vertical_gap = bbox[1] - last_y1 if b['page'] == last_page else body_size * 2
        gap_factor = min(2.0, vertical_gap / body_size) # Cap the factor at 2
        score += gap_factor * Config.W_VERTICAL_GAP

        # Bonus scores
        if b['bold']: score += Config.W_IS_BOLD
        if len(text.split()) > 4 or ':' in text: score += Config.W_TEXT_LENGTH
        
        scored_candidates.append({'block': b, 'score': score})
        last_y1 = bbox[3]
        last_page = b['page']

    if not scored_candidates: return []

    # Phase 2: Adaptive classification based on score distribution
    scores = np.array([c['score'] for c in scored_candidates])
    if len(scores) < 3: # Not enough data, just assume H1/H2 based on score
        h1_threshold = np.mean(scores)
    else: # Use score distribution to find a natural break for H1
        h1_threshold = np.mean(scores) + np.std(scores) * 0.8
        
    h2_threshold = np.mean(scores) * 0.9

    outline = []
    for candidate in scored_candidates:
        b, score = candidate['block'], candidate['score']
        level = 'H3' # Default to H3
        if score >= h1_threshold: level = 'H1'
        elif score >= h2_threshold: level = 'H2'
        
        normalized_text = normalize_text(b['text'])
        is_numbered = numbered_heading_regex and numbered_heading_regex.match(normalized_text)
        if is_numbered:
            normalized_text = numbered_heading_regex.sub('', normalized_text).strip()
        
        if len(normalized_text) >= Config.HEADING_MIN_CHARS:
            outline.append({"level": level, 'text': normalized_text, 'page': b['page']})
            
    return outline

def extract_outline(path: Path, lang_settings: Dict) -> Optional[Dict[str, Any]]:
    try:
        doc = fitz.open(path)
    except Exception as e:
        print(f"  ❌ Failed to open PDF '{path.name}': {e}"); return None
        
    blocks = extract_text_blocks(doc)
    title = detect_title(doc, blocks)
    
    embedded_toc = doc.get_toc(simple=True)
    if embedded_toc:
        print("  ℹ️ Found embedded outline. Using it directly.")
        return {'title': title, 'outline': format_embedded_toc(embedded_toc)}

    print("  ⚠️ No embedded outline found. Using heuristic analysis.")
    if not blocks:
        print("  ❌ No text blocks found."); return None
    return {'title': title, 'outline': classify_headings(blocks, title, lang_settings)}

def main():
    parser = argparse.ArgumentParser(description="Extract a structured outline from PDF files.")
    parser.add_argument("input_dir", type=str, help="Directory with input PDF files.")
    parser.add_argument("output_dir", type=str, help="Directory to save JSON output.")
    parser.add_argument("--lang", type=str, default="en", help="Language of documents (e.g., 'en', 'zh').")
    args = parser.parse_args()

    lang_configs = load_language_config()
    if not lang_configs: return
    
    if args.lang not in lang_configs:
        print(f"❌ Language '{args.lang}' not found in '{Config.LANG_CONFIG_FILE}'."); return
        
    lang_settings = lang_configs[args.lang]
    input_path, output_path = Path(args.input_dir), Path(args.output_dir)
    output_path.mkdir(exist_ok=True)
    pdf_files = list(input_path.glob('*.pdf'))
    if not pdf_files:
        print(f"⚠️ No PDF files found in '{input_path}'."); return

    print(f"🚀 Starting processing for {len(pdf_files)} PDF files with language '{args.lang}'.\n")
    for pdf in pdf_files:
        print(f"Processing '{pdf.name}'...")
        result = extract_outline(pdf, lang_settings)
        if result:
            output_file = output_path / f'{pdf.stem}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  ✅ Successfully extracted outline to '{output_file.name}'")
        else:
            print(f"  ❌ Could not extract outline from '{pdf.name}'.")
        print("-" * 20)
    print("\n🎉 All files processed.")

if __name__ == '__main__':
    main()