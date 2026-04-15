FROM nginx:1.26-alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf

# SSL certs must be placed in docker/nginx/ssl/ before building
COPY docker/nginx/ssl/ /etc/nginx/ssl/

RUN chown -R nginx:nginx /var/cache/nginx /var/log/nginx && \
    chmod 600 /etc/nginx/ssl/*.key 2>/dev/null || true

EXPOSE 80 443
