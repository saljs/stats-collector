FROM python:3.12-alpine

# Install packages
RUN apk add build-base tzdata

# copy the requirements file into the image
COPY ./requirements.txt /app/requirements.txt

# change workdir
WORKDIR /app

# install requirements
RUN pip install -r requirements.txt

# copy the rest of the files
COPY . .

# Expose default port
EXPOSE 5000

# Set env variables
ENV FLASK_APP=api_server.py
ENV TZ=America/Chicago

# set entrypoint cmd
ENTRYPOINT ["python"]
CMD ["-m", "flask", "run", "--host", "0.0.0.0"]
