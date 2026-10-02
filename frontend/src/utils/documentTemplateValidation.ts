import type { AnalyseDefinitions, FieldDefinition } from "@/types/documentTemplate";

// Validation côté client d'un modèle de document, affichée avant l'enregistrement. Elle reprend les règles du
// serveur (backend issue #138), qui reste l'autorité : tout placeholder du fichier doit avoir un champ défini,
// et tout champ défini doit être dans le fichier.

export type IssueKind =
  | "unknown_placeholder"
  | "unused_field"
  | "invalid_name"
  | "duplicate_name"
  | "missing_label"
  | "incomplete_source"
  | "unknown_source"
  | "missing_name";

export interface ValidationIssue {
  kind: IssueKind;
  /** Nom du champ ou du placeholder concerné. */
  name: string;
  message: string;
}

const FIELD_NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;
// Mots réservés du moteur de gabarit : « loop » sert aux boucles, les autres sont des littéraux.
const RESERVED = new Set(["loop", "true", "false", "none", "True", "False", "None", "self", "caller", "varargs", "kwargs"]);

export function isValidFieldName(name: string): boolean {
  return FIELD_NAME.test(name) && !RESERVED.has(name);
}

export function validateTemplate(
  placeholders: string[],
  fields: FieldDefinition[],
  definitions: AnalyseDefinitions | null = null,
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const names = new Set<string>();
  const seen = new Set<string>();

  for (const field of fields) {
    if (!field.name) {
      issues.push({ kind: "missing_name", name: "", message: "Un champ n'a pas de nom." });
      continue;
    }
    if (!isValidFieldName(field.name)) {
      issues.push({
        kind: "invalid_name",
        name: field.name,
        message: `« ${field.name} » n'est pas un nom de champ valide (lettres, chiffres et _, sans mot réservé).`,
      });
    }
    if (seen.has(field.name)) {
      issues.push({ kind: "duplicate_name", name: field.name, message: `Le champ « ${field.name} » est défini plusieurs fois.` });
    }
    seen.add(field.name);
    names.add(field.name);
    if (!field.label.trim()) {
      issues.push({ kind: "missing_label", name: field.name, message: `Le champ « ${field.name} » n'a pas de libellé.` });
    }
    if (field.source.kind === "analysis" && !field.source.definitionName.trim()) {
      issues.push({
        kind: "incomplete_source",
        name: field.name,
        message: `Le champ « ${field.name} » tire sa valeur de l'analyse : indiquez le nom de l'élément.`,
      });
    }
    // Un modèle appartient à une analyse : la source ne peut désigner qu'un élément que cette analyse définit
    // (les relations et les champs « renseignés » n'ont pas de définition à vérifier).
    if (definitions && field.source.kind === "analysis" && field.source.definitionName.trim()) {
      const kind = field.source.elementKind;
      if (kind === "entity" || kind === "classification" || kind === "synthesis") {
        const known = definitions[kind].map((n) => n.trim().toLowerCase());
        if (!known.includes(field.source.definitionName.trim().toLowerCase())) {
          issues.push({
            kind: "unknown_source",
            name: field.name,
            message: `Le champ « ${field.name} » désigne « ${field.source.definitionName} », que l'analyse ne définit pas.`,
          });
        }
      }
    }
    if (!placeholders.includes(field.name)) {
      issues.push({
        kind: "unused_field",
        name: field.name,
        message: `Le champ « ${field.name} » n'a pas de placeholder dans le fichier : supprimez-le ou ajoutez {{ ${field.name} }} au modèle.`,
      });
    }
  }
  for (const placeholder of placeholders) {
    if (!names.has(placeholder)) {
      issues.push({
        kind: "unknown_placeholder",
        name: placeholder,
        message: `Le placeholder {{ ${placeholder} }} du fichier n'a pas de champ défini.`,
      });
    }
  }
  return issues;
}

/** Champ créé par défaut pour un placeholder détecté : texte obligatoire, renseigné au fil de l'instruction. */
export function defaultField(name: string): FieldDefinition {
  return { name, label: name, type: "text", required: true, instruction: "", source: { kind: "instruction" } };
}
