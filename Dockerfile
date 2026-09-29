# Site estático (HTML + CSS + JS) servido pelo Nginx
FROM nginx:alpine

# Copia apenas os arquivos do site para a pasta pública do Nginx
COPY index.html main.js /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY img/ /usr/share/nginx/html/img/

EXPOSE 80

# O Nginx já inicia por padrão na imagem oficial, mas deixamos explícito
CMD ["nginx", "-g", "daemon off;"]
