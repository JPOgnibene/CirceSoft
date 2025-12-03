# Use Node.js 20 to satisfy Vite requirements
FROM node:20-alpine 

# Set the working directory inside the container
WORKDIR /app

# Copy the dependency files first to leverage Docker layer caching
COPY package.json package-lock.json ./

# Install dependencies (equivalent to 'npm install')
RUN npm install

# Copy the rest of the application code
COPY . .

# EXPOSE the port the application listens on (Vite default)
EXPOSE 5173

# Command to run the development server, binding to all interfaces
CMD ["npm", "run", "dev", "--", "--host"]
