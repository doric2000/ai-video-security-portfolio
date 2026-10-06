FROM nginx:1.27-alpine

RUN mkdir -p /usr/share/nginx/html/assets
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY static/index.html /usr/share/nginx/html/index.html
COPY static/styles.css /usr/share/nginx/html/assets/styles.css
COPY static/app.js /usr/share/nginx/html/assets/app.js
