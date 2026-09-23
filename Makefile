.PHONY: up down front logs build rebuild clean prod

# Démarre la stack complète avec hot reload (docker-compose.override.yaml
# est fusionné automatiquement). Le frontend tourne sur http://localhost:5173.
up:
	docker compose up --build

# Démarre la stack "production-like" (nginx sur :8081, sans Vite HMR).
prod:
	docker compose -f docker-compose.yaml up --build

# Démarre uniquement le frontend Vite avec hot reload.
# (le backend doit déjà tourner : `docker compose up -d backend` au préalable)
front:
	docker compose up --build frontend

# Arrête la stack.
down:
	docker compose down

# Tail les logs de tous les services.
logs:
	docker compose logs -f

# Rebuild toutes les images sans cache.
rebuild:
	docker compose build --no-cache

# Arrête et supprime conteneurs + volumes (destructif !).
clean:
	docker compose down -v
