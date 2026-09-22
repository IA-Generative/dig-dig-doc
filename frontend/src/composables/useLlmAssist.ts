// Mocked "aide LLM" suggestions until a real LLM-backed endpoint exists on
// the BFF. Kept separate from useAnalyses (the data store) so the two
// concerns - persistence vs. suggestion content - don't mix.
import type { AgentCapability, EntityDefinition, EntityType, LabelDefinition } from "@/types/analyse";

const promptTemplates: Record<AgentCapability, string> = {
  "Classification documentaire":
    "Tu es un agent de classification documentaire. Analyse le document fourni et retourne une catégorie " +
    "normalisée parmi les labels définis, avec un score de confiance.",
  "Extraction d'entités nommées":
    "Tu es un agent d'extraction d'entités nommées. Extrait les entités définies au format JSON strict, " +
    "sans inventer de champ absent du document.",
  "Contrôle de cohérence":
    "Tu es un agent de contrôle de cohérence. Compare les entités extraites entre les pièces du dossier et signale " +
    "les incohérences (valide / incohérence_détectée / vérification_manuelle_requise) en citant les champs divergents.",
  "Agent généraliste": "Tu es un agent généraliste. Décris précisément la tâche que tu dois accomplir sur le dossier.",
};

const suggestedLabels: Omit<LabelDefinition, "id">[] = [
  { name: "CNI", definition: "Carte nationale d'identité française, recto ou verso." },
  { name: "Passeport", definition: "Passeport français ou étranger en cours de validité." },
  { name: "Justificatif de domicile", definition: "Facture, quittance ou attestation de moins de 3 mois." },
  { name: "Avis d'imposition", definition: "Avis d'impôt sur le revenu émis par la DGFiP." },
  { name: "Autre", definition: "Tout document ne correspondant à aucune autre catégorie." },
];

const suggestedEntities: Omit<EntityDefinition, "id">[] = [
  { name: "Nom", definition: "Nom de famille tel qu'il apparaît sur le document.", type: "texte" },
  { name: "Prénom", definition: "Premier prénom d'usage.", type: "texte" },
  { name: "Date de naissance", definition: "Date de naissance au format JJ/MM/AAAA.", type: "date" },
  { name: "Adresse postale", definition: "Adresse complète : numéro, voie, code postal, ville.", type: "texte" },
  { name: "Numéro de pièce", definition: "Numéro d'identification unique du document.", type: "identifiant" },
];

export function suggestPrompt(capability: AgentCapability): string {
  return promptTemplates[capability];
}

export function suggestLabels(): LabelDefinition[] {
  return suggestedLabels.map((label, index) => ({ ...label, id: `label-suggestion-${index}` }));
}

export function suggestEntities(): EntityDefinition[] {
  return suggestedEntities.map((entity, index) => ({ ...entity, id: `entity-suggestion-${index}` }));
}

/** Suggère une définition pour un label déjà nommé, à partir de son nom. */
export function suggestLabelDefinition(name: string): string {
  const match = suggestedLabels.find((label) => label.name.toLowerCase() === name.trim().toLowerCase());
  if (match) return match.definition;
  if (!name.trim()) return "Décris précisément ce que recouvre ce label.";
  return `Document de type "${name.trim()}", à préciser (contenu attendu, mentions obligatoires...).`;
}

/** Suggère une définition et un type pour une entité déjà nommée, à partir de son nom. */
export function suggestEntityDefinition(name: string): { definition: string; type: EntityType } {
  const match = suggestedEntities.find((entity) => entity.name.toLowerCase() === name.trim().toLowerCase());
  if (match) return { definition: match.definition, type: match.type };
  if (!name.trim()) return { definition: "Décris précisément la valeur à extraire pour cette entité.", type: "texte" };
  return { definition: `Valeur de "${name.trim()}" telle qu'elle apparaît sur le document.`, type: "texte" };
}
