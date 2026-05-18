FROM nginx:1.25-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf

RUN mkdir -p /var/www/static

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1
