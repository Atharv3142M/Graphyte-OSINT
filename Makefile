up:
	docker-compose up -d

down:
	docker-compose down

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install



