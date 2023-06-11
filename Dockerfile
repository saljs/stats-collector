FROM python:3.11-alpine

# Install packages
RUN apk add build-base

# copy the requirements file into the image
COPY ./requirements.txt /app/requirements.txt

# change workdir
WORKDIR /app

# install requirements
RUN pip install -r requirements.txt

# copy the rest of the files
COPY . /app

# Expose default port
EXPOSE 5000

# Set env variables
ENV FLASK_APP=stats_collector.py

# set entrypoint cmd
ENTRYPOINT ["python"]
CMD ["flask", "run", "--host", "0.0.0.0"]
