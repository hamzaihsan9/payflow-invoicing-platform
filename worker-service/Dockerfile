FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --omit=dev || true

COPY . .

EXPOSE 5001

CMD ["node", "server.js"]
