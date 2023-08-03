FROM alpine:latest

# Install packages
RUN apk add mysql-client supercronic

# change workdir
WORKDIR /app

# install files
COPY . .

# set up default env variables
ENV KEEP_DAYS 4

# set entrypoint cmd
ENTRYPOINT ["supercronic"]
CMD ["backups.cron"]
