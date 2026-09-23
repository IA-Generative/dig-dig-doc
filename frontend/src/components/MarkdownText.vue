<script setup lang="ts">
import { computed } from "vue";
import { marked } from "marked";

const props = withDefaults(defineProps<{
  content: string;
  /** Tronque le rendu à N lignes (via line-clamp CSS). */
  lines?: number;
}>(), {
  lines: 0,
});

// Configuration : pas de HTML autorisé dans le source (sécurité XSS), le
// markdown seul est converti. marked.parse renvoie du HTML sûr tant que
// l'option mangle/headerIds n'est pas activée (désactivées par défaut
// depuis marked v5+).
marked.setOptions({
  breaks: true,
  gfm: true,
});

const html = computed(() => {
  if (!props.content) return "";
  return marked.parse(props.content, { async: false }) as string;
});

const style = computed(() => {
  if (props.lines > 0) {
    return {
      display: "-webkit-box",
      "-webkit-line-clamp": String(props.lines),
      "line-clamp": String(props.lines),
      "-webkit-box-orient": "vertical",
      overflow: "hidden",
    } as Record<string, string>;
  }
  return undefined;
});
</script>

<template>
  <div class="markdown-text" :style="style" v-html="html" />
</template>

<style scoped>
.markdown-text {
  line-height: 1.6;
}

.markdown-text :deep(p) {
  margin: 0 0 0.5rem;
}

.markdown-text :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-text :deep(ul),
.markdown-text :deep(ol) {
  margin: 0 0 0.5rem;
  padding-left: 1.25rem;
}

.markdown-text :deep(li) {
  margin: 0.125rem 0;
}

.markdown-text :deep(strong) {
  font-weight: 600;
}

.markdown-text :deep(em) {
  font-style: italic;
}

.markdown-text :deep(code) {
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  background: var(--background-alt-grey);
  font-size: 0.875em;
  font-family: monospace;
}

.markdown-text :deep(blockquote) {
  margin: 0 0 0.5rem;
  padding-left: 0.75rem;
  border-left: 3px solid var(--border-default-grey);
  color: var(--text-mention-grey);
}

.markdown-text :deep(h1),
.markdown-text :deep(h2),
.markdown-text :deep(h3),
.markdown-text :deep(h4) {
  margin: 0.5rem 0 0.25rem;
  font-weight: 600;
}

.markdown-text :deep(h1) { font-size: 1.25rem; }
.markdown-text :deep(h2) { font-size: 1.125rem; }
.markdown-text :deep(h3) { font-size: 1rem; }
.markdown-text :deep(h4) { font-size: 0.875rem; }

.markdown-text :deep(a) {
  color: var(--text-active-blue-france);
  text-decoration: underline;
}

.markdown-text :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.5rem 0;
}

.markdown-text :deep(th),
.markdown-text :deep(td) {
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--border-default-grey);
}

.markdown-text :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-default-grey);
  margin: 0.5rem 0;
}
</style>
