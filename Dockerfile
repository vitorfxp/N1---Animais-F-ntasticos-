FROM nginx:alpine

COPY index.html main.js /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY img/ /usr/share/nginx/html/img/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
