FROM node:20-alpine

WORKDIR /app

# Instalar pnpm v9 (compatible con el lockfile del proyecto)
RUN npm install -g pnpm@9

# Copiar definiciones de dependencias
COPY frontend/package.json frontend/pnpm-lock.yaml* frontend/.npmrc* ./

# Instalar dependencias usando pnpm
RUN pnpm install --frozen-lockfile=false

# Copiar código del frontend
COPY frontend/ .

EXPOSE 5173

CMD ["pnpm", "run", "dev", "--host"]