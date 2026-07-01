# Avtobaholash — Deployment Qo'llanmasi

## Tezkor ishga tushirish (Local)

### 1. Talab qilinadigan dasturlar
```bash
# Docker & Docker Compose
docker --version        # 24+
docker compose version  # 2.x

# Node.js (frontend uchun)
node --version          # 18+
```

### 2. Backend ishga tushirish
```bash
cd avtobaholash/

# .env fayl yaratish
cp .env.example .env
# .env faylni to'ldiring (DB, Redis, AI kalitlar)

# Docker bilan ishga tushirish
docker compose -f docker/docker-compose.yml up -d db redis minio

# Virtual environment
python -m venv venv && source venv/bin/activate

# Paketlarni o'rnatish
pip install -r requirements/development.txt

# Ma'lumotlar bazasi migratsiyasi
python manage.py migrate

# Demo ma'lumotlar yaratish (himoya uchun)
python manage.py create_demo_data

# Django development server
python manage.py runserver
```

### 3. Frontend ishga tushirish
```bash
cd avtobaholash-frontend/

# Paketlarni o'rnatish
npm install

# .env.local yaratish
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local

# Development server
npm run dev
```

### 4. Celery (AI baholash uchun)
```bash
# Alohida terminal
cd avtobaholash/
source venv/bin/activate
celery -A config worker -l info
```

---

## Production Deploy (Docker Compose)

```bash
# Barcha servislari bir vaqtda ishga tushirish
docker compose -f docker/docker-compose.yml up -d

# Migratsiya
docker compose exec web python manage.py migrate

# Demo ma'lumot
docker compose exec web python manage.py create_demo_data

# Static fayllar
docker compose exec web python manage.py collectstatic --noinput
```

---

## URL manzillar

| Servis | URL | Izoh |
|--------|-----|------|
| Frontend | http://localhost:3000 | Next.js |
| Backend API | http://localhost:8000/api/v1/ | Django DRF |
| Admin panel | http://localhost:8000/admin/ | Django Admin |
| MinIO console | http://localhost:9001 | Fayl storage |

---

## Login ma'lumotlari (Demo)

| Rol | Email | Parol |
|-----|-------|-------|
| Bosh Admin | admin@avtobaholash.uz | Admin@2025 |
| Kafedra mudiri | mudiri@avtobaholash.uz | Mudiri@2025 |
| O'qituvchi | teacher@avtobaholash.uz | Teacher@2025 |
| Talaba | student@avtobaholash.uz | Student@2025 |

---

## Muhim konfiguratsiyalar (.env)

```env
SECRET_KEY=your-secret-key-here
DJANGO_SETTINGS_MODULE=config.settings.development

DB_NAME=avtobaholash
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://localhost:6379/0

ANTHROPIC_API_KEY=sk-ant-...   # AI baholash uchun
TELEGRAM_BOT_TOKEN=...          # Bildirishnomalar uchun

MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=avtobaholash
MINIO_ENDPOINT=http://localhost:9000
```

---

## Himoya uchun demo scenario

1. **Login** → admin@avtobaholash.uz bilan kiring
2. **Admin dashboard** → statistikalarni ko'rsating
3. **Kafedralar** → yangi kafedra qo'shing
4. **Foydalanuvchilar** → o'qituvchi va talaba qo'shing
5. teacher@avtobaholash.uz bilan login
6. **Topshiriq yarating** → test turida
7. **Savollar yuklang** → 5-10 ta savol
8. **Nashr qiling** → talabalarga yuborildi
9. student@avtobaholash.uz bilan login
10. **Topshiriqni ko'ring** → imtihon interfeysi
11. mudiri@avtobaholash.uz bilan login
12. **Dashboard** → AI tahlil va o'qituvchi baholari
