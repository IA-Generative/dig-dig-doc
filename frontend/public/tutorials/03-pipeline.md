# Lancer le pipeline d'instruction

## Classification et extraction

Une fois vos documents importés dans un dossier rattaché à une analyse,
le pipeline d'instruction peut être lancé.

1. Ouvrez le dossier concerné.
2. Cliquez sur le bouton **Lancer l'analyse**.
3. Le pipeline s'exécute en plusieurs étapes :
   - **Classification** : chaque document est catégorisé (CNI, passeport,
     justificatif de domicile, etc.) avec un score de confiance.
   - **Extraction** : les entités clés (nom, prénom, date de naissance,
     adresse, numéros) sont extraites et structurées en JSON.
   - **Cohérence** : les données sont croisées entre pièces pour détecter
     les incohérences ou informations manquantes.

## Suivre la progression

- L'onglet **Classification** affiche les résultats par document.
- L'onglet **Extraction** présente les entités extraites sous forme
  structurée.
- L'onglet **Agents** montre les résultats des agents IA spécialisés.

## Corriger les résultats

- Chaque champ extrait peut être **corrigé** manuellement.
- Les classifications peuvent être **modifiées** si l'IA s'est trompée.
- Vos corrections sont enregistrées automatiquement.

> **Astuce** : si un document n'est pas classé correctement, vérifiez sa
> qualité (résolution, luminosité) et relancez l'analyse si nécessaire.
