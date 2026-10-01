export interface TextSegment {
  text: string;
  highlighted: boolean;
}

const ELLIPSIS = /^(?:\.{2,}|…|\s)+|(?:\.{2,}|…|\s)+$/g;

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// Regex tolérante : mots de l'extrait séparés par n'importe quel blanc
// (l'extrait a été aplati côté worker, le texte de la page garde ses sauts
// de ligne), insensible à la casse.
function toLooseRegExp(fragment: string): RegExp | null {
  const words = fragment.split(/\s+/).filter(Boolean).map(escapeRegExp);
  if (words.length === 0) return null;
  return new RegExp(words.join("\\s+"), "i");
}

/**
 * Découpe le texte d'une page en segments, en surlignant l'endroit d'où vient
 * l'extrait cité. L'extrait est un résumé de la zone (fenêtre tronquée avec
 * des « ... »), il peut donc ne pas correspondre mot pour mot : on essaie
 * l'extrait entier, puis son plus long fragment entre ellipses/sauts de
 * ligne, puis ses premiers mots. Sans correspondance, aucun surlignage.
 */
export function highlightExcerpt(content: string, excerpt: string | null | undefined): TextSegment[] {
  const plain: TextSegment[] = [{ text: content, highlighted: false }];
  const cleaned = (excerpt ?? "").replace(ELLIPSIS, "").trim();
  if (!content || !cleaned) return plain;

  const longestFragment = cleaned
    .split(/\.{2,}|…|\n/)
    .map((fragment) => fragment.trim())
    .sort((a, b) => b.length - a.length)[0];
  const firstWords = cleaned.split(/\s+/).slice(0, 8).join(" ");

  for (const candidate of [cleaned, longestFragment, firstWords]) {
    const regex = candidate ? toLooseRegExp(candidate) : null;
    const match = regex ? regex.exec(content) : null;
    if (match && match[0].length >= 3) {
      const start = match.index;
      const end = start + match[0].length;
      return [
        { text: content.slice(0, start), highlighted: false },
        { text: content.slice(start, end), highlighted: true },
        { text: content.slice(end), highlighted: false },
      ].filter((segment) => segment.text.length > 0);
    }
  }
  return plain;
}
