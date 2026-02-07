# Use Nginx Alpine for a lightweight web server
FROM nginx:alpine

# Copy static frontend files to Nginx html directory
COPY . /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
