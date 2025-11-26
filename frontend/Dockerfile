FROM node:18

WORKDIR /app

COPY package*.json ./
RUN npm ci --silent

COPY . /app

EXPOSE 5173

# Run dev server to make local development simple. For production, build+serve with nginx.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
