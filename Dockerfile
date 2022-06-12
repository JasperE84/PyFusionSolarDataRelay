FROM python:3.10-slim
WORKDIR /code

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Run updates
RUN apt-get clean && apt-get update && apt-get upgrade -y

# Set the locale
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "-u", "pv.py", "-v"]
