# WebAPI / Database

Dette projekt kører som en **WebAPI med database** via Docker / Docker Compose.

## Krav

For at køre projektet skal følgende være installeret:

- Docker
- docker-compose

---

# Opsætning

Før du kan køre projektet, skal du oprette en `.env` fil.

Du kan enten:

- oprette en ny fil kaldet `.env`
- eller kopiere `.env.example` og omdøbe den
---

# Environment Variables

I `.env` filen skal følgende variabler defineres:

| Env Variable | Beskrivelse | Eksempel |
|---|---|---|
| DATABASE_URL | URL til databasen. Da databasen er SQLite kan du bare bruge eksemplet | sqlite:///./data/app.db |
| API_PORT | Port som WebAPI skal køre på | 8000 |

---

# Start WebAPI

Når variablerne er defineret kan du starte API’en:

```bash
docker-compose up -d
```

Dette starter API’en i baggrunden.

Herefter kan du åbne den genererede Swagger-side i browseren:

```
http://localhost:API_PORT/docs
```

---

# Stop API

For at stoppe API’en:

```bash
docker-compose down
```

For også at fjerne containers og volumes:

```bash
docker-compose rm
```
