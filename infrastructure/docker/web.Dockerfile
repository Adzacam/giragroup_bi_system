FROM node:20-alpine

WORKDIR /app

# 1. Habilitar o instalar pnpm globalmente
RUN npm install -g pnpm

# 2. Copiar package.json (y pnpm-lock.yaml si ya existe)
COPY frontend/package.json frontend/pnpm-lock.yaml* ./

# 3. Instalar dependencias usando la caché eficiente de pnpm
RUN pnpm install

# 4. Copiar el resto del código
COPY frontend/ .

EXPOSE 5173

# 5. Ejecutar Vite usando pnpm
CMD ["pnpm", "run", "dev", "--host"]