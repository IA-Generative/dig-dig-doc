<script setup lang="ts">
import { useAuth } from "@/composables/useAuth";

const { isAuthenticated, loading, login } = useAuth();

const features = [
  {
    icon: "ri-file-search-line",
    title: "Classification documentaire",
    description:
      "Identification automatique de la nature de chaque pièce téléversée (CNI, passeport, justificatif de domicile, avis d'imposition…) avec un score de confiance.",
  },
  {
    icon: "ri-text-snippet",
    title: "Extraction d'entités",
    description:
      "Extraction des informations clés (nom, prénom, date de naissance, adresse, numéros) structurées en JSON, sans saisie manuelle.",
  },
  {
    icon: "ri-shield-check-line",
    title: "Contrôles de cohérence",
    description:
      "Croisement des données entre pièces d'un même dossier pour détecter incohérences, fraudes ou informations manquantes.",
  },
  {
    icon: "ri-chat-3-line",
    title: "Assistant conversationnel",
    description:
      "Posez des questions sur vos dossiers et obtenez des réponses contextualisées, avec citation des sources consultées.",
  },
  {
    icon: "ri-folder-shield-2-line",
    title: "Souveraineté des données",
    description:
      "Authentification Keycloak, stockage souverain et chiffrement. Vos données restent en France, rien n'est réutilisé pour le réentraînement.",
  },
  {
    icon: "ri-flow-chart",
    title: "Pipelines d'agents",
    description:
      "Configurez des agents IA spécialisés par analyse, avec des outils et des prompts personnalisés pour chaque cas d'usage.",
  },
];

const steps = [
  {
    num: 1,
    icon: "ri-upload-2-line",
    title: "Importez vos documents",
    description: "Déposez vos fichiers (PDF, images, tableurs) dans un dossier usager.",
  },
  {
    num: 2,
    icon: "ri-cpu-line",
    title: "L'IA analyse le contenu",
    description: "Classification, extraction d'entités et contrôles de cohérence automatiques.",
  },
  {
    num: 3,
    icon: "ri-chat-check-line",
    title: "Discutez avec l'assistant",
    description: "Posez des questions, enrichissez les synthèses et validez les résultats.",
  },
  {
    num: 4,
    icon: "ri-check-double-line",
    title: "Vérifiez et exportez",
    description: "Consultez les résultats, corrigez si besoin et finalisez votre dossier.",
  },
];
</script>

<template>
  <div class="welcome">
    <!-- Hero -->
    <section class="welcome__hero">
      <div class="fr-container welcome__hero-inner">
        <p class="welcome__badge">Plateforme d'instruction assistée par IA</p>
        <h1 class="welcome__title">
          Accélérez l'instruction<br />de vos dossiers usagers
        </h1>
        <p class="welcome__subtitle">
          Importez vos documents, laissez l'IA extraire et structurer les
          informations clés, vérifiez la cohérence entre pièces et échangez
          avec un assistant conversationnel — le tout sur une infrastructure
          souveraine.
        </p>
        <div class="welcome__actions">
          <button
            v-if="!isAuthenticated && !loading"
            type="button"
            class="fr-btn fr-btn--lg"
            @click="login()"
          >
            Se connecter
          </button>
          <RouterLink
            v-if="isAuthenticated"
            to="/analyses"
            class="fr-btn fr-btn--lg"
          >
            Accéder à l'application
          </RouterLink>
          <a href="#features" class="fr-btn fr-btn--secondary fr-btn--lg">
            Découvrir les fonctionnalités
          </a>
        </div>
      </div>
    </section>

    <!-- Fonctionnalités -->
    <section id="features" class="welcome__section">
      <div class="fr-container">
        <h2 class="welcome__section-title">Ce que dig-dig-doc vous apporte</h2>
        <p class="welcome__section-subtitle">
          Une suite d'outils d'IA pour fiabiliser et accélérer le traitement
          documentaire, de l'import à la validation.
        </p>
        <div class="welcome__feature-grid">
          <div
            v-for="feature in features"
            :key="feature.title"
            class="welcome__feature-card"
          >
            <span class="welcome__feature-icon-wrapper">
              <VIcon :name="feature.icon" class="welcome__feature-icon" />
            </span>
            <h3 class="welcome__feature-title">{{ feature.title }}</h3>
            <p class="welcome__feature-desc">{{ feature.description }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Étapes -->
    <section class="welcome__section welcome__section--alt">
      <div class="fr-container">
        <h2 class="welcome__section-title">Comment ça marche ?</h2>
        <p class="welcome__section-subtitle">
          Quatre étapes, de l'import du document à l'export du dossier validé.
        </p>
        <div class="welcome__step-grid">
          <div
            v-for="step in steps"
            :key="step.num"
            class="welcome__step"
          >
            <div class="welcome__step-header">
              <span class="welcome__step-num">{{ step.num }}</span>
              <VIcon :name="step.icon" class="welcome__step-icon" />
            </div>
            <h3 class="welcome__step-title">{{ step.title }}</h3>
            <p class="welcome__step-desc">{{ step.description }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="welcome__cta">
      <div class="fr-container welcome__cta-inner">
        <h2 class="welcome__cta-title">Prêt à commencer ?</h2>
        <p class="welcome__cta-text">
          Connectez-vous pour accéder à votre espace de travail et créer vos
          premières analyses.
        </p>
        <div class="welcome__actions">
          <button
            v-if="!isAuthenticated && !loading"
            type="button"
            class="fr-btn fr-btn--lg"
            @click="login()"
          >
            Se connecter
          </button>
          <RouterLink
            v-if="isAuthenticated"
            to="/analyses"
            class="fr-btn fr-btn--lg"
          >
            Accéder à l'application
          </RouterLink>
        </div>
      </div>
    </section>

    <footer class="welcome__footer">
      <div class="fr-container welcome__footer-inner">
        <p>dig-dig-doc — Instruction assistée des dossiers usagers</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.welcome {
  min-height: 100vh;
  background: var(--background-default-grey);
}

/* ── Hero ─────────────────────────────────────────────── */
.welcome__hero {
  background: linear-gradient(
    135deg,
    var(--background-alt-blue-france) 0%,
    var(--background-alt-grey) 100%
  );
  padding: 4rem 0 5rem;
}

.welcome__hero-inner {
  max-width: 50rem;
  text-align: center;
}

.welcome__badge {
  display: inline-block;
  padding: 0.375rem 1rem;
  border-radius: 1rem;
  background: var(--background-action-low-blue-france);
  color: var(--text-action-high-blue-france);
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: 1.5rem;
}

.welcome__title {
  font-size: clamp(2rem, 5vw, 3.25rem);
  font-weight: 700;
  color: var(--text-action-high-blue-france);
  margin: 0 0 1.25rem;
  line-height: 1.15;
}

.welcome__subtitle {
  font-size: 1.125rem;
  color: var(--text-default-grey);
  line-height: 1.6;
  margin: 0 auto 2.5rem;
  max-width: 38rem;
}

.welcome__actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

/* ── Sections génériques ──────────────────────────────── */
.welcome__section {
  padding: 4rem 0;
}

.welcome__section--alt {
  background: var(--background-alt-grey);
}

.welcome__section-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-title-grey);
  text-align: center;
  margin: 0 0 0.75rem;
}

.welcome__section-subtitle {
  font-size: 1.0625rem;
  color: var(--text-mention-grey);
  text-align: center;
  margin: 0 auto 3rem;
  max-width: 36rem;
  line-height: 1.5;
}

/* ── Cartes fonctionnalités ───────────────────────────── */
.welcome__feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
  gap: 1.5rem;
}

.welcome__feature-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 2rem 1.75rem;
  background: var(--background-default-grey);
  border: 1px solid var(--border-default-grey);
  border-radius: 0.5rem;
  transition:
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}

.welcome__feature-card:hover {
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
  border-color: var(--border-action-high-blue-france);
}

.welcome__feature-icon-wrapper {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 0.5rem;
  background: var(--background-action-low-blue-france);
  margin-bottom: 1.25rem;
}

.welcome__feature-icon {
  font-size: 1.5rem;
  color: var(--text-action-high-blue-france);
}

.welcome__feature-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-title-grey);
  margin: 0 0 0.5rem;
}

.welcome__feature-desc {
  font-size: 0.9375rem;
  color: var(--text-mention-grey);
  line-height: 1.55;
  margin: 0;
}

/* ── Étapes ───────────────────────────────────────────── */
.welcome__step-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 2rem;
}

.welcome__step {
  text-align: center;
}

.welcome__step-header {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.welcome__step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 50%;
  background: var(--background-action-high-blue-france);
  color: var(--text-inverted-blue-france);
  font-size: 1rem;
  font-weight: 700;
}

.welcome__step-icon {
  font-size: 1.5rem;
  color: var(--text-action-high-blue-france);
}

.welcome__step-title {
  font-size: 1.0625rem;
  font-weight: 600;
  color: var(--text-title-grey);
  margin: 0 0 0.5rem;
}

.welcome__step-desc {
  font-size: 0.9375rem;
  color: var(--text-mention-grey);
  line-height: 1.55;
  margin: 0;
}

/* ── CTA ──────────────────────────────────────────────── */
.welcome__cta {
  padding: 4rem 0;
  text-align: center;
  background: linear-gradient(
    135deg,
    var(--background-alt-blue-france) 0%,
    var(--background-alt-grey) 100%
  );
}

.welcome__cta-inner {
  max-width: 40rem;
}

.welcome__cta-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-action-high-blue-france);
  margin: 0 0 0.75rem;
}

.welcome__cta-text {
  font-size: 1.125rem;
  color: var(--text-default-grey);
  margin: 0 0 2rem;
}

/* ── Footer ───────────────────────────────────────────── */
.welcome__footer {
  padding: 1.5rem 0;
  background: var(--background-default-grey);
  border-top: 1px solid var(--border-default-grey);
}

.welcome__footer-inner {
  text-align: center;
}

.welcome__footer p {
  font-size: 0.875rem;
  color: var(--text-mention-grey);
  margin: 0;
}

/* ── Responsive ───────────────────────────────────────── */
@media (max-width: 768px) {
  .welcome__hero {
    padding: 2.5rem 0 3.5rem;
  }

  .welcome__section {
    padding: 2.5rem 0;
  }

  .welcome__cta {
    padding: 2.5rem 0;
  }
}
</style>
