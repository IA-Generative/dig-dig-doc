import { ref } from "vue";

/**
 * État partagé de la modale de l'agent helper : permet de l'ouvrir depuis
 * n'importe où (menu utilisateur, raccourci clavier, chat d'un dossier) en
 * lui transmettant éventuellement le dossier courant comme point de départ.
 * Le contexte se limite à une référence au dossier, pas à son contenu.
 */
export interface HelperDossierContext {
  dossierId: string;
  name: string;
}

const isOpen = ref(false);
const dossierContext = ref<HelperDossierContext | null>(null);

export function useHelperAgent() {
  function openHelper(context: HelperDossierContext | null = null) {
    dossierContext.value = context;
    isOpen.value = true;
  }

  function closeHelper() {
    isOpen.value = false;
    dossierContext.value = null;
  }

  // Le contexte n'est utilisé que pour le premier message envoyé.
  function consumeContext() {
    dossierContext.value = null;
  }

  return { isOpen, dossierContext, openHelper, closeHelper, consumeContext };
}
