Dette er min WebAPI / Database

For at køre dette skal du bruge Docker/docker-compose.

Før du kan køre det skal du lave en ny fil der heder .env du kan også kopier .env.example og omdøb den.

Heri skal du definere 2 Enviorenment Variabler:
Env Variable | Indhold | Eksemple
--- | --- | ---
DATABASE_URL | Dette url til database, da databasen er SQLite kan du bare kopier Eksemplet her | sqlite:///./data/app.db
API_PORT | Dette er porten denne API skal køre på | 8000

Når disse er defineret kan du køre<br>
`docker-compose up -d`<br>
For at køre programmet i baggrunden og så kan du gå til `localhost:API_PORT/docs` og se en genereret Swagger page

Når du vil ligge det ned igen kan du køre<br>
`docker-compose down`<br>
Herefter kan du køre dette for at sikre containers/volumes bliver slettet korrekt<br>
`docker-compose rm`
