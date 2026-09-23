<script setup lang="ts">
import { useAuth } from "@/composables/useAuth";

const { isAuthenticated, loading, login } = useAuth();

const features = [
  {
    icon: "ri-file-search-line",
    title: "Analyse de documents",
    description: "Importez vos dossiers usagers et laissez l'IA extraire et structurer automatiquement les informations clés.",
  },
  {
    icon: "ri-shield-check-line",
    title: "Vérification de cohérence",
    description: "Croisez les données entre documents pour détecter les incohérences et les informations manquantes.",
  },
  {
    icon: "ri-chat-3-line",
    title: "Assistant conversationnel",
    description: "Posez des questions sur vos dossiers et obtenez des réponses contextualisées grâce à l'IA générative.",
  },
  {
    icon: "ri-folder-shield-2-line",
    title: "Sécurité & souveraineté",
    description: "Authentification Keycloak, stockage souverain et chiffrement. Vos données restent en France.",
  },
];

const steps = [
  {
    num: 1,
    title: "Importez vos documents",
    description: "Déposez vos fichiers (PDF, images, tableurs) dans un dossier usager.",
  },
  {
    num: 2,
    title: "L'IA analyse le contenu",
    description: "Extraction de texte, classification et reconnaissance d'entités automatiques.",
  },
  {
    num: 3,
    title: "Vérifiez et validez",
    description: "Consultez les résultats, corrigez si besoin et exportez votre dossier.",
  },
];
</script>

<template>
  <div class="welcome">
    <!-- En-tête plein écran avec l'accroche -->
    <section class="welcome__hero">
      <div class="welcome__hero-content">
        <p class="welcome__badge">Plateforme d'instruction assistée</p>
        <h1 class="welcome__title">dig-dig-doc</h1>
        <p class="welcome__subtitle">
          Instruction assistée des dossiers usagers.
          Importez, analysez et vérifiez vos documents grâce à l'intelligence artificielle.
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
          <a
            href="#features"
            class="fr-btn fr-btn--secondary fr-btn--lg"
          >
            En savoir plus
          </a>
        </div>
      </div>
    </section>

    <!-- Section fonctionnalités -->
    <section id="features" class="welcome__features">
      <h2 class="welcome__section-title">Ce que dig-dig-doc vous apporte</h2>
      <div class="welcome__feature-grid">
        <div v-for="feature in features" :key="feature.title" class="welcome__feature-card">
          <VIcon :name="feature.icon" class="welcome__feature-icon" />
          <h3 class="welcome__feature-title">{{ feature.title }}</h3>
          <p class="welcome__feature-desc">{{ feature.description }}</p>
        </div>
      </div>
    </section>

    <!-- Section étapes -->
    <section class="welcome__steps">
      <h2 class="welcome__section-title">Comment ça marche ?</h2>
      <div class="welcome__step-grid">
        <div v-for="step in steps" :key="step.num" class="welcome__step">
          <span class="welcome__step-num">{{ step.num }}</span>
          <h3 class="welcome__step-title">{{ step.title }}</h3>
          <p class="welcome__step-desc">{{ step.description }}</p>
        </div>
      </div>
    </section>

    <!-- CTA final -->
    <section class="welcome__cta">
      <h2 class="welcome__cta-title">Prêt à commencer ?</h2>
      <p class="welcome__cta-text">Connectez-vous pour accéder à votre espace de travail.</p>
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
    </section>

    <footer class="welcome__footer">
      <p>dig-dig-doc — Instruction assistée des dossiers usagers</p>
    </footer>
  </div>
</template>

<style scoped>
.welcome {
  min-height: 100vh;
  background: var(--background-alt-blue-france);
}

/* Hero plein écran */
.welcome__hero {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 70vh;
  padding: 3rem 1.5rem;
  background: linear-gradient(135deg, var(--background-alt-blue-france) 0%, var(--background-alt-grey) 100%);
}

.welcome__hero-content {
  max-width: 48rem;
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
  font-size: clamp(2.5rem, 6vw, 4rem);
  font-weight: 700;
  color: var(--text-action-high-blue-france);
  margin: 0 0 1rem;
  line-height: 1.1;
}

.welcome__subtitle {
  font-size: 1.25rem;
  color: var(--text-default-grey);
  line-height: 1.6;
  margin: 0 auto 2.5rem;
  max-width: 36rem;
}

.welcome__actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

/* Section fonctionnalités */
.welcome__features {
  padding: 4rem 1.5rem;
  max-width: 72rem;
  margin: 0 auto;
}

.welcome__section-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-title-grey);
  text-align: center;
  margin: 0 0 2.5rem;
}

.welcome__feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 1.5rem;
}

.welcome__feature-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 2rem 1.5rem;
  background: var(--background-default-grey);
  border: 1px solid var(--border-default-grey);
  border-radius: 0.5rem;
  transition: box-shadow 0.2s ease;
}

.welcome__feature-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.welcome__feature-icon {
  font-size: 2.5rem;
  color: var(--text-action-high-blue-france);
  margin-bottom: 1rem;
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
  line-height: 1.5;
  margin: 0;
}

/* Section étapes */
.welcome__steps {
  padding: 4rem 1.5rem;
  background: var(--background-default-grey);
}

.welcome__step-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 2rem;
  max-width: 72rem;
  margin: 0 auto;
}

.welcome__step {
  text-align: center;
}

.welcome__step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  background: var(--background-action-high-blue-france);
  color: var(--text-inverted-blue-france);
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1rem;
}

.welcome__step-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-title-grey);
  margin: 0 0 0.5rem;
}

.welcome__step-desc {
  font-size: 0.9375rem;
  color: var(--text-mention-grey);
  line-height: 1.5;
  margin: 0;
}

/* CTA final */
.welcome__cta {
  padding: 4rem 1.5rem;
  text-align: center;
  background: var(--background-alt-blue-france);
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

/* Footer */
.welcome__footer {
  padding: 1.5rem;
  text-align: center;
  background: var(--background-default-grey);
  border-top: 1px solid var(--border-default-grey);
}

.welcome__footer p {
  font-size: 0.875rem;
  color: var(--text-mention-grey);
  margin: 0;
}
</style>
