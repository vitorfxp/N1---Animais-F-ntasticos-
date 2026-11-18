# Site estático do mapa de tráfego (HTML + CSS + JS) servido pelo Nginx.
# Os dados vêm de /api/, que o Apache do host encaminha para a API do monitoramento.
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html main.js /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY img/ /usr/share/nginx/html/img/
COPY js/ /usr/share/nginx/html/js/
COPY data/ /usr/share/nginx/html/data/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
