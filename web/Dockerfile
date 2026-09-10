FROM node:22-alpine
WORKDIR /srv
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build
EXPOSE 3001
CMD ["npm", "run", "start"]
